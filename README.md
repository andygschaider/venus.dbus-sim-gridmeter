# venus.dbus-sim-gridmeter
A service for Venus OS, running entirely on the Victron Energy DBus for simulation of a reacting grid meter,
based on given values from existing ac load meters and existing pv inverters. 

The Python script reads power data from all available ac loads using the service name "com.victronenergy.acload.\*"
and all available pv inverters using the service name "com.victronenergy.pvinverter.\*".

Then it calculates the grid meter data using the formula "load - generation".

Finally it publishes the calculated values as a new simulated grid meter on the DBus, using the service name "com.victronenergy.grid.simgridmeter".

## Configuration
There are no configuration options.
Feel free to make suggestions on what should be configurable - the script however is designed to work with all acload and pvinverter setups so i guess configuration will not be a use case in the future.
## Installation
SSH to your Device and use the following commands one after eachother:

```opkg update```

```opkg install git```

```cd /data```

```git clone https://github.com/andygschaider/venus.dbus-sim-gridmeter dbus-sim-gridmeter```

```cd dbus-sim-gridmeter```

```chmod 755 install.sh```

```./install.sh```

After running install.sh the service should be configured and running.

## Credits
Thanks a lot to https://github.com/Waldmensch1 for designing https://github.com/Waldmensch1/venus.dbus-sma-smartmeter, which inspired me implementing this script.
Furthermore a few other projects helped a lot with basic understanding:
* https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py
* https://github.com/mr-manuel/venus-os_dbus-multiplus-emulator/blob/master/dbus-multiplus-emulator/dbus-multiplus-emulator.py
* https://github.com/victronenergy/dbus_vebus_to_pvinverter
* https://github.com/RalfZim/venus.dbus-fronius-smartmeter
* https://github.com/h4ckst0ck/dbus-solaredge

Credits also go to https://chatgpt.com/ for explaining code snippets :D.

And last but not least thanks a lot for the great documentation from Victron themselves: https://github.com/victronenergy/venus/wiki/howto-add-a-driver-to-Venus