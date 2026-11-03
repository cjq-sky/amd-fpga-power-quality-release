`timescale 1ns/1ps
// Same-clock, one-entry elastic R channel. Reset is deliberately synchronous:
// an upstream asynchronous-reset FIFO status must not directly drive the
// VDMA line-buffer RAM write-enable pins. No address or burst semantics change.
(* KEEP_HIERARCHY="yes" *) module vdma_mm2s_r_slice (
 input wire clk, input wire resetn,
 input wire [31:0] s_rdata, input wire [1:0] s_rresp,
 input wire s_rlast, input wire s_rvalid, output wire s_rready,
 output reg [31:0] m_rdata, output reg [1:0] m_rresp,
 output reg m_rlast, output wire m_rvalid, input wire m_rready
);
 (* KEEP="TRUE" *) reg buffered_valid;
 reg enabled;
 assign s_rready=enabled && (!buffered_valid || m_rready);
 assign m_rvalid=buffered_valid;
 always @(posedge clk) begin
  if(!resetn) begin
   enabled<=0; buffered_valid<=0;
   m_rdata<=0; m_rresp<=0; m_rlast<=0;
  end else begin
   enabled<=1;
   if(s_rready) begin
    buffered_valid<=s_rvalid;
    if(s_rvalid) begin
     m_rdata<=s_rdata; m_rresp<=s_rresp; m_rlast<=s_rlast;
    end
   end
  end
 end
endmodule
