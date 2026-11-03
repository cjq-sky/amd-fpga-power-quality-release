`timescale 1ns/1ps
// Same physical shared H16 BUFG as the manager. No ownership read side effects.
module lab07_raw_memory_bridge(
 input wire clk,aresetn,main_reset,
 input wire owner_valid,owner_bank,
 input wire [31:0] owner_token,owner_fid,
 input wire [7:0] owner_status,
 input wire ack_reservation,
 output wire read_busy,read_start,
 output reg raw_read_en,raw_read_bank_id,
 output reg [10:0] raw_read_index,
 input wire raw_read_valid,
 input wire [31:0] raw_read_data,
 input wire [31:0] s_axi_awaddr,s_axi_wdata,s_axi_araddr,
 input wire [2:0] s_axi_awprot,s_axi_arprot,
 input wire [3:0] s_axi_wstrb,
 input wire s_axi_awvalid,s_axi_wvalid,s_axi_bready,s_axi_arvalid,s_axi_rready,
 output wire s_axi_awready,s_axi_wready,s_axi_arready,
 output reg s_axi_bvalid,s_axi_rvalid,
 output reg [1:0] s_axi_bresp,s_axi_rresp,
 output reg [31:0] s_axi_rdata
);
 localparam IDLE=2'd0,REQUEST=2'd1,RETURN=2'd2,RESPONSE=2'd3;
 reg [1:0] state;
 reg [31:0] request_token,request_fid;
 reg aw_pending,w_pending;
 assign read_busy=state!=IDLE;
 assign s_axi_arready=aresetn && state==IDLE && !ack_reservation;
 assign read_start=s_axi_arready && s_axi_arvalid;
 assign s_axi_awready=aresetn && !aw_pending && !s_axi_bvalid;
 assign s_axi_wready=aresetn && !w_pending && !s_axi_bvalid;
 wire legal=owner_valid && owner_token!=0 && owner_status==8'h01 && !main_reset &&
            s_axi_araddr<32'h2000 && s_axi_araddr[1:0]==0;
 always @(posedge clk) begin
  if(!aresetn) begin
   state<=IDLE;raw_read_en<=0;raw_read_bank_id<=0;raw_read_index<=0;
   request_token<=0;request_fid<=0;s_axi_rvalid<=0;s_axi_rdata<=0;s_axi_rresp<=0;
   aw_pending<=0;w_pending<=0;s_axi_bvalid<=0;s_axi_bresp<=0;
  end else begin
   raw_read_en<=0;
   case(state)
    IDLE: if(read_start) begin
     raw_read_bank_id<=owner_bank;raw_read_index<=s_axi_araddr[12:2];
     request_token<=owner_token;request_fid<=owner_fid;
     if(legal) begin raw_read_en<=1;state<=REQUEST;end
     else begin s_axi_rvalid<=1;s_axi_rdata<=0;s_axi_rresp<=2'b10;state<=RESPONSE;end
    end
    REQUEST: state<=RETURN; // manager samples registered request here (E1).
    RETURN: begin // Only E2 may consume the matching synchronous return.
     s_axi_rvalid<=1;state<=RESPONSE;
     if(raw_read_valid && !main_reset && owner_valid &&
        owner_bank==raw_read_bank_id && owner_token==request_token && owner_fid==request_fid) begin
      s_axi_rdata<=raw_read_data;s_axi_rresp<=0;
     end else begin s_axi_rdata<=0;s_axi_rresp<=2'b10;end
    end
    RESPONSE: if(s_axi_rvalid && s_axi_rready) begin s_axi_rvalid<=0;state<=IDLE;end
   endcase
   // Data writes never reach manager memory. Pair independent AW/W tokens.
   if(s_axi_awready && s_axi_awvalid) aw_pending<=1;
   if(s_axi_wready && s_axi_wvalid) w_pending<=1;
   if(aw_pending && w_pending && !s_axi_bvalid) begin
    aw_pending<=0;w_pending<=0;s_axi_bvalid<=1;s_axi_bresp<=2'b10;
   end else if(s_axi_bvalid && s_axi_bready) s_axi_bvalid<=0;
  end
 end
endmodule
