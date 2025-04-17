#!/usr/bin/env python3

from gi.repository import GLib
import platform
import argparse
import logging
import sys
import os
import dbus

# velib packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
from vedbus import VeDbusItemImport, VeDbusService


class DbusSimGridMeterService(object):
    def __init__(self, servicename, deviceinstance, paths, productname='Simulated Grid Meter',
                 connection='Simulated Grid Meter Service', productid=0):
        self._dbusservice = VeDbusService(servicename)
        self._paths = paths
        self.bus = dbus.SystemBus()
        logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

        # Load existing AC meters
        self.ac_meters = self.find_services_by_type('acload')
        logging.info(f"Aktive AC-Load-Services erkannt: {self.ac_meters}")

        # Initialise item list for all existing AC meters
        self._ac_meter_itemlist = {}
        for meter_name in self.ac_meters:
            itemlist = self.init_read_items(meter_name)
            self._ac_meter_itemlist[meter_name] = itemlist
        # logging.debug(f"_ac_meter_itemlist: {self._ac_meter_itemlist}")

        # Load existing PV inverters
        self.pv_inverters = self.find_services_by_type('pvinverter')
        logging.info(f"Aktive PV-Inverter-Services erkannt: {self.pv_inverters}")

        # Initialise item list for all existing PV inverters
        self._pv_inverter_itemlist = {}
        for inverter_name in self.pv_inverters:
            itemlist = self.init_read_items(inverter_name)
            self._pv_inverter_itemlist[inverter_name] = itemlist
        # logging.debug(f"_pv_inverter_itemlist: {self._pv_inverter_itemlist}")

        # Load overall PV generation from com.victronenergy.system
        # self.system = 'com.victronenergy.system'
        # Initialise item list for PV generation from system
        # self.systempathlist = {
        #    '/Ac/PvOnGrid/L1/Current': {'initial': 0},
        #    '/Ac/PvOnGrid/L2/Current': {'initial': 0},
        #    '/Ac/PvOnGrid/L3/Current': {'initial': 0},
        #    '/Ac/PvOnGrid/L1/Power': {'initial': 0},
        #    '/Ac/PvOnGrid/L2/Power': {'initial': 0},
        #    '/Ac/PvOnGrid/L3/Power': {'initial': 0},
        # }
        # self.system_itemlist = {}
        # for path in self.systempathlist:
        #    item = VeDbusItemImport(
        #        bus=self.bus,
        #        serviceName=servicename,
        #        path=path,
        #        eventCallback=None
        #    )
        #    self.system_itemlist[path] = item

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion',
                                   'Unkown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        self._dbusservice.add_path('/ProductId', productid)
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/FirmwareVersion', 1)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 1)

        # create paths in DBus for this fake grid meter
        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path, settings['initial'], writeable=True, onchangecallback=self._handlechangedvalue)

        # register service after all paths for the newly created fake grid meter have been added
        self._dbusservice.register()
        # Führe alle 100ms _update(self) aus
        GLib.timeout_add(100, self._update)

    def find_services_by_type(self, device_type):
        # Durchsucht den D-Bus nach einem bestimmten Gerätetyp (z. B. 'grid', 'acload', 'pvinverter)
        service_list = []
        for service in self.bus.list_names():
            if service.startswith(f'com.victronenergy.{device_type}.'):
                service_list.append(service)
        return service_list

    # VeDbusItemImport für alle zu lesenden Pfade des unter "servicename" angegebenen Geräts initialisieren
    def init_read_items(self, servicename):
        itemDict = {
            "servicename": servicename
        }
        for path in self._paths:
            item = VeDbusItemImport(
                bus=self.bus,
                serviceName=servicename,
                path=path,
                eventCallback=None
            )
            itemDict[path] = item
        return itemDict

    def read_item_values(self, itemlist):
        itemDict = {}
        for path in self._paths:
            try:
                item = itemlist[path]
                value = item.get_value()
                itemDict[path] = value
            except Exception as e:
                print(f"Fehler beim Auslesen: {e}")
        return itemDict

    # This function is only neccessary if the pv sum is taken from the com.victronenergy.system
    # def read_single_value(self, path):
    #    try:
    #        return path.get_value()
    #    except Exception as e:
    #        print(f"Fehler beim Auslesen: {e}")
    #        return

    def _update(self):
        # Read in the current AC meter values for every existing AC meter
        ac_meter_values = {}
        ac_meter_sum = {}
        for path in self._paths:
            ac_meter_sum[path] = 0
        for meter_name in self.ac_meters:
            itemvalues = self.read_item_values(self._ac_meter_itemlist[meter_name])
            # Sum up all ac meter values
            for path in self._paths:
                if path == '/Ac/L1/Voltage' or path == '/Ac/L2/Voltage' or path == '/Ac/L3/Voltage':
                    ac_meter_sum[path] = ((ac_meter_sum[path] + itemvalues[path]) / 2) if ac_meter_sum[path] > 0 else \
                    itemvalues[path]
                else:
                    ac_meter_sum[path] = ac_meter_sum[path] + itemvalues[path]
            ac_meter_values[meter_name] = itemvalues
        # logging.debug(f"ac_meter_values: {ac_meter_values}")

        # Read in the current PV inverter values
        pv_inverter_values = {}
        pv_inverter_sum = {}
        for path in self._paths:
            pv_inverter_sum[path] = 0
        for inverter_name in self.pv_inverters:
            itemvalues = self.read_item_values(self._pv_inverter_itemlist[inverter_name])
            # Sum up all pv inverter values
            for path in self._paths:
                if path == '/Ac/L1/Voltage' or path == '/Ac/L2/Voltage' or path == '/Ac/L3/Voltage':
                    pv_inverter_sum[path] = ((pv_inverter_sum[path] + (itemvalues[path]) or 0) / 2) if pv_inverter_sum[
                                                                                                           path] > 0 else (
                                itemvalues[
                                    path] or 0)  # the "or 0" is necessary if the pv inverters have been without pv power for longer than ca. 2 hours, since they then go into deep sleep mode and give a null value
                else:
                    pv_inverter_sum[path] = pv_inverter_sum[path] + (itemvalues[path] or 0)
            pv_inverter_values[inverter_name] = itemvalues
        # logging.debug(f"pv_inverter_sum: {pv_inverter_sum}")

        # Base the sum upon the values from com.victronenergy.system
        # pv_inverter_sum = {
        #    '/Ac/PvOnGrid/L1/Current': self.read_single_value('/Ac/PvOnGrid/L1/Current'),
        #    '/Ac/PvOnGrid/L2/Current': self.read_single_value('/Ac/PvOnGrid/L2/Current'),
        #    '/Ac/PvOnGrid/L3/Current': self.read_single_value('/Ac/PvOnGrid/L3/Current'),
        #    '/Ac/PvOnGrid/L1/Power': self.read_single_value('/Ac/PvOnGrid/L1/Power'),
        #    '/Ac/PvOnGrid/L2/Power': self.read_single_value('/Ac/PvOnGrid/L2/Power'),
        #    '/Ac/PvOnGrid/L3/Power': self.read_single_value('/Ac/PvOnGrid/L3/Power'),
        # }
        # logging.debug(f"pv_inverter_sum: {pv_inverter_sum}")

        # Compute the grid meter values
        grid_meter_values = {}
        for path in self._paths:
            grid_meter_values[path] = 0
        for path in self._paths:
            if path == '/Ac/L1/Voltage' or path == '/Ac/L2/Voltage' or path == '/Ac/L3/Voltage':
                grid_meter_values[path] = (ac_meter_sum[path] + pv_inverter_sum[path]) / 2
            else:
                grid_meter_values[path] = ac_meter_sum[path] - pv_inverter_sum[path]

        # Write the grid meter values
        for path in self._paths:
            self._dbusservice[path] = grid_meter_values[path]
        # logging.debug(f"Updating value...")

        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change


# === All code below is to simply run it from the commandline for debugging purposes ===

# It will created a dbus service called com.victronenergy.pvinverter.output.
# To try this on commandline, start this program in one terminal, and try these commands
# from another terminal:
# dbus com.victronenergy.pvinverter.output
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward GetValue
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward SetValue %20
#
# Above examples use this dbus client: http://code.google.com/p/dbus-tools/wiki/DBusCli
# See their manual to explain the % in %20

def main():
    logging.basicConfig(level=logging.DEBUG)

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    fakeGridMeterService = DbusSimGridMeterService(
        servicename='com.victronenergy.grid.simgridmeter',
        deviceinstance=0,
        paths={
            '/Ac/Power': {'initial': 0},
            '/Ac/L1/Voltage': {'initial': 0},
            '/Ac/L2/Voltage': {'initial': 0},
            '/Ac/L3/Voltage': {'initial': 0},
            '/Ac/L1/Current': {'initial': 0},
            '/Ac/L2/Current': {'initial': 0},
            '/Ac/L3/Current': {'initial': 0},
            '/Ac/L1/Power': {'initial': 0},
            '/Ac/L2/Power': {'initial': 0},
            '/Ac/L3/Power': {'initial': 0},
        })

    # logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
