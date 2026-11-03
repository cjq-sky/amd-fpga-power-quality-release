`timescale 1ns/1ps
// System-only adapter. Standard interconnect gates the assigned aperture.
module lab07_dc0_raw #(parameter [31:0] RAW_BASE_ADDRESS=32'h0)(
(* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 s_axi_aclk CLK", X_INTERFACE_PARAMETER="ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 125000000" *)
input wire  s_axi_aclk,
(* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 s_axi_aresetn RST", X_INTERFACE_PARAMETER="POLARITY ACTIVE_LOW" *)
input wire  s_axi_aresetn,
input wire  main_reset,
input wire  owner_valid,
input wire  owner_bank,
input wire [31:0] owner_token,
input wire [31:0] owner_fid,
input wire [7:0] owner_status,
input wire  ack_reservation,
output wire  read_busy,
output wire  read_start,
output wire  raw_read_en,
output wire  raw_read_bank_id,
output wire [10:0] raw_read_index,
input wire  raw_read_valid,
input wire [31:0] raw_read_data,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *)
input wire [31:0] s_axi_awaddr,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
input wire [31:0] s_axi_wdata,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
input wire [31:0] s_axi_araddr,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI AWPROT" *)
input wire [2:0] s_axi_awprot,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI ARPROT" *)
input wire [2:0] s_axi_arprot,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
input wire [3:0] s_axi_wstrb,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
input wire  s_axi_awvalid,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
input wire  s_axi_wvalid,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
input wire  s_axi_bready,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
input wire  s_axi_arvalid,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
input wire  s_axi_rready,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
output wire  s_axi_awready,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
output wire  s_axi_wready,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
output wire  s_axi_arready,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
output wire  s_axi_bvalid,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
output wire  s_axi_rvalid,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
output wire [1:0] s_axi_bresp,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
output wire [1:0] s_axi_rresp,
(* X_INTERFACE_INFO="xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
output wire [31:0] s_axi_rdata
);
lab07_raw_memory_bridge u_slave(
.clk(s_axi_aclk),
.aresetn(s_axi_aresetn),
.main_reset(main_reset),
.owner_valid(owner_valid),
.owner_bank(owner_bank),
.owner_token(owner_token),
.owner_fid(owner_fid),
.owner_status(owner_status),
.ack_reservation(ack_reservation),
.read_busy(read_busy),
.read_start(read_start),
.raw_read_en(raw_read_en),
.raw_read_bank_id(raw_read_bank_id),
.raw_read_index(raw_read_index),
.raw_read_valid(raw_read_valid),
.raw_read_data(raw_read_data),
.s_axi_awaddr(s_axi_awaddr - RAW_BASE_ADDRESS),
.s_axi_wdata(s_axi_wdata),
.s_axi_araddr(s_axi_araddr - RAW_BASE_ADDRESS),
.s_axi_awprot(s_axi_awprot),
.s_axi_arprot(s_axi_arprot),
.s_axi_wstrb(s_axi_wstrb),
.s_axi_awvalid(s_axi_awvalid),
.s_axi_wvalid(s_axi_wvalid),
.s_axi_bready(s_axi_bready),
.s_axi_arvalid(s_axi_arvalid),
.s_axi_rready(s_axi_rready),
.s_axi_awready(s_axi_awready),
.s_axi_wready(s_axi_wready),
.s_axi_arready(s_axi_arready),
.s_axi_bvalid(s_axi_bvalid),
.s_axi_rvalid(s_axi_rvalid),
.s_axi_bresp(s_axi_bresp),
.s_axi_rresp(s_axi_rresp),
.s_axi_rdata(s_axi_rdata)
);
endmodule
