`timescale 1ns/1ps
// One outstanding read and one independent write. Both resets abort the whole
// bridge epoch. The attached slave must also be reset by m_resetn_out.
// Payloads are bundled data: held before request/ack synchronizer traversal,
// and held until the return-to-zero handshake completes. See bridge_cdc.xdc.
(* KEEP_HIERARCHY="yes" *) module vdma_axil_snapshot_bridge #(
 parameter integer ADDR_WIDTH=9
)(
 input wire s_aclk, input wire m_aclk, input wire resetn,
 output wire s_resetn_out, output wire m_resetn_out,
 input wire [ADDR_WIDTH-1:0] s_axi_awaddr,
 input wire s_axi_awvalid, output wire s_axi_awready,
 input wire [31:0] s_axi_wdata,
 input wire s_axi_wvalid, output wire s_axi_wready,
 output reg [1:0] s_axi_bresp, output reg s_axi_bvalid, input wire s_axi_bready,
 input wire [ADDR_WIDTH-1:0] s_axi_araddr,
 input wire s_axi_arvalid, output wire s_axi_arready,
 output reg [31:0] s_axi_rdata, output reg [1:0] s_axi_rresp,
 output reg s_axi_rvalid, input wire s_axi_rready,
 output reg [ADDR_WIDTH-1:0] m_axi_awaddr,
 output reg m_axi_awvalid, input wire m_axi_awready,
 output reg [31:0] m_axi_wdata,
 output reg m_axi_wvalid, input wire m_axi_wready,
 input wire [1:0] m_axi_bresp, input wire m_axi_bvalid, output wire m_axi_bready,
 output reg [ADDR_WIDTH-1:0] m_axi_araddr,
 output reg m_axi_arvalid, input wire m_axi_arready,
 input wire [31:0] m_axi_rdata, input wire [1:0] m_axi_rresp,
 input wire m_axi_rvalid, output wire m_axi_rready
);
 (* ASYNC_REG="TRUE" *) reg [2:0] srst, mrst;
 always @(posedge s_aclk or negedge resetn)
  if(!resetn) srst<=0; else srst<={srst[1:0],1'b1};
 always @(posedge m_aclk or negedge resetn)
  if(!resetn) mrst<=0; else mrst<={mrst[1:0],1'b1};
 assign s_resetn_out=srst[2]; assign m_resetn_out=mrst[2];

 reg r_req, r_ack, w_req, w_ack;
 (* ASYNC_REG="TRUE" *) reg [1:0] r_req_sync, r_ack_sync, w_req_sync, w_ack_sync;
 always @(posedge m_aclk or negedge m_resetn_out)
  if(!m_resetn_out) begin r_req_sync<=0;w_req_sync<=0;end
  else if(!mrst[2]) begin r_req_sync<=0;w_req_sync<=0;end
  else begin r_req_sync<={r_req_sync[0],r_req};w_req_sync<={w_req_sync[0],w_req};end
 always @(posedge s_aclk or negedge s_resetn_out)
  if(!s_resetn_out) begin r_ack_sync<=0;w_ack_sync<=0;end
  else if(!srst[2]) begin r_ack_sync<=0;w_ack_sync<=0;end
  else begin r_ack_sync<={r_ack_sync[0],r_ack};w_ack_sync<={w_ack_sync[0],w_ack};end

 reg [ADDR_WIDTH-1:0] read_address_hold, write_address_hold;
 reg [31:0] write_data_hold;
 reg [33:0] read_snapshot;
 reg [1:0] write_snapshot;
 reg [1:0] s_read_state, m_read_state, s_write_state, m_write_state;
 reg aw_full, w_full;
 assign s_axi_arready=srst[2] && s_read_state==0;
 assign s_axi_awready=srst[2] && s_write_state==0 && !aw_full;
 assign s_axi_wready=srst[2] && s_write_state==0 && !w_full;
 assign m_axi_rready=mrst[2] && m_read_state==2;
 assign m_axi_bready=mrst[2] && m_write_state==2;

 always @(posedge s_aclk or negedge s_resetn_out) begin
  if(!s_resetn_out) begin
   s_read_state<=0;r_req<=0;read_address_hold<=0;
   s_axi_rdata<=0;s_axi_rresp<=0;s_axi_rvalid<=0;
   s_write_state<=0;w_req<=0;aw_full<=0;w_full<=0;
   write_address_hold<=0;write_data_hold<=0;s_axi_bresp<=0;s_axi_bvalid<=0;
  end else if(!srst[2]) begin
   s_read_state<=0;r_req<=0;s_axi_rvalid<=0;
   s_write_state<=0;w_req<=0;aw_full<=0;w_full<=0;s_axi_bvalid<=0;
  end else begin
   case(s_read_state)
    0: if(s_axi_arvalid && s_axi_arready) begin
     read_address_hold<=s_axi_araddr;r_req<=1;s_read_state<=1;
    end
    1: if(r_ack_sync[1]) begin
     {s_axi_rresp,s_axi_rdata}<=read_snapshot;
     s_axi_rvalid<=1;s_read_state<=2;
    end
    2: if(s_axi_rvalid && s_axi_rready) begin
     s_axi_rvalid<=0;r_req<=0;s_read_state<=3;
    end
    3: if(!r_ack_sync[1]) s_read_state<=0;
   endcase
   case(s_write_state)
    0: begin
     if(s_axi_awvalid && s_axi_awready) begin write_address_hold<=s_axi_awaddr;aw_full<=1;end
     if(s_axi_wvalid && s_axi_wready) begin write_data_hold<=s_axi_wdata;w_full<=1;end
     if(aw_full && w_full) begin w_req<=1;s_write_state<=1;end
    end
    1: if(w_ack_sync[1]) begin s_axi_bresp<=write_snapshot;s_axi_bvalid<=1;s_write_state<=2;end
    2: if(s_axi_bvalid && s_axi_bready) begin s_axi_bvalid<=0;w_req<=0;s_write_state<=3;end
    3: if(!w_ack_sync[1]) begin aw_full<=0;w_full<=0;s_write_state<=0;end
   endcase
  end
 end

 always @(posedge m_aclk or negedge m_resetn_out) begin
  if(!m_resetn_out) begin
   m_read_state<=0;r_ack<=0;read_snapshot<=0;m_axi_araddr<=0;m_axi_arvalid<=0;
   m_write_state<=0;w_ack<=0;write_snapshot<=0;
   m_axi_awaddr<=0;m_axi_awvalid<=0;m_axi_wdata<=0;m_axi_wvalid<=0;
  end else if(!mrst[2]) begin
   m_read_state<=0;r_ack<=0;m_axi_arvalid<=0;
   m_write_state<=0;w_ack<=0;m_axi_awvalid<=0;m_axi_wvalid<=0;
  end else begin
   case(m_read_state)
    0: if(r_req_sync[1]) begin m_axi_araddr<=read_address_hold;m_axi_arvalid<=1;m_read_state<=1;end
    1: if(m_axi_arvalid && m_axi_arready) begin m_axi_arvalid<=0;m_read_state<=2;end
    2: if(m_axi_rvalid && m_axi_rready) begin
     read_snapshot<={m_axi_rresp,m_axi_rdata};r_ack<=1;m_read_state<=3;
    end
    3: if(!r_req_sync[1]) begin r_ack<=0;m_read_state<=0;end
   endcase
   case(m_write_state)
    0: if(w_req_sync[1]) begin
     m_axi_awaddr<=write_address_hold;m_axi_wdata<=write_data_hold;
     m_axi_awvalid<=1;m_axi_wvalid<=1;m_write_state<=1;
    end
    1: begin
     if(m_axi_awvalid && m_axi_awready) m_axi_awvalid<=0;
     if(m_axi_wvalid && m_axi_wready) m_axi_wvalid<=0;
     if((!m_axi_awvalid || m_axi_awready) && (!m_axi_wvalid || m_axi_wready)) m_write_state<=2;
    end
    2: if(m_axi_bvalid && m_axi_bready) begin write_snapshot<=m_axi_bresp;w_ack<=1;m_write_state<=3;end
    3: if(!w_req_sync[1]) begin w_ack<=0;m_write_state<=0;end
   endcase
  end
 end
endmodule
