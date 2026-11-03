## Lab 02B: exact digital mapping from reports/wiring_plan.md.
set_property PACKAGE_PIN H16 [get_ports clk_125mhz]
set_property IOSTANDARD LVCMOS33 [get_ports clk_125mhz]
create_clock -period 8.000 -name clk_125mhz [get_ports clk_125mhz]

set_property PACKAGE_PIN R14 [get_ports led0]
set_property IOSTANDARD LVCMOS33 [get_ports led0]

set_property PACKAGE_PIN F19 [get_ports {ad_data[0]}]
set_property PACKAGE_PIN V10 [get_ports {ad_data[1]}]
set_property PACKAGE_PIN V8  [get_ports {ad_data[2]}]
set_property PACKAGE_PIN W10 [get_ports {ad_data[3]}]
set_property PACKAGE_PIN B20 [get_ports {ad_data[4]}]
set_property PACKAGE_PIN W8  [get_ports {ad_data[5]}]
set_property PACKAGE_PIN V6  [get_ports {ad_data[6]}]
set_property PACKAGE_PIN Y6  [get_ports {ad_data[7]}]
set_property PACKAGE_PIN B19 [get_ports {ad_data[8]}]
set_property PACKAGE_PIN U7  [get_ports {ad_data[9]}]
set_property PACKAGE_PIN C20 [get_ports {ad_data[10]}]
set_property PACKAGE_PIN Y8  [get_ports {ad_data[11]}]
set_property PACKAGE_PIN A20 [get_ports {ad_data[12]}]
set_property PACKAGE_PIN Y9  [get_ports {ad_data[13]}]
set_property PACKAGE_PIN U8  [get_ports {ad_data[14]}]
set_property PACKAGE_PIN W6  [get_ports {ad_data[15]}]
set_property IOSTANDARD LVCMOS33 [get_ports {ad_data[*]}]

set_property PACKAGE_PIN Y7  [get_ports ad_busy]
set_property PACKAGE_PIN F20 [get_ports ad_frstdata]
set_property PACKAGE_PIN W9  [get_ports ad_convst]
set_property PACKAGE_PIN Y18 [get_ports ad_reset]
set_property PACKAGE_PIN Y19 [get_ports ad_cs_n]
set_property PACKAGE_PIN U18 [get_ports ad_rd_n]
set_property IOSTANDARD LVCMOS33 [get_ports {ad_busy ad_frstdata ad_convst ad_reset ad_cs_n ad_rd_n}]

## BUSY is asynchronous; its only consumer is the first synchronizer register.
## Use the stable top-level port name so this exception survives RTL renaming.
set_false_path -from [get_ports ad_busy]
