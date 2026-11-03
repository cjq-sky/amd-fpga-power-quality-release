`timescale 1ns/1ps
// Core-clock register router. Existing bundled-data AXIL bridge remains the
// sole CDC boundary. Local registers occupy 0x100..0x1fc, absent in static use.
module frame_retire_registers(
 input wire clk,resetn, engine_seen,prior_armed,started,busy,accepted,retire_valid,
 input wire [63:0] accepted_seq,retire_seq,
 input wire [1:0] active_slot,retire_slot,
 input wire [31:0] fence_error,
 output reg enable,req,consume,protocol_error,
 output wire [127:0] generation,
 output wire [31:0] base0,base1,base2,base3,
 output wire [63:0] req_seq,consume_seq,
 output wire [1:0] req_slot,
 input wire [8:0] s_awaddr,input wire s_awvalid,output wire s_awready,
 input wire [31:0] s_wdata,input wire s_wvalid,output wire s_wready,
 output reg [1:0] s_bresp,output reg s_bvalid,input wire s_bready,
 input wire [8:0] s_araddr,input wire s_arvalid,output wire s_arready,
 output reg [31:0] s_rdata,output reg [1:0] s_rresp,output reg s_rvalid,input wire s_rready,
 output reg [8:0] m_awaddr,output reg m_awvalid,input wire m_awready,
 output reg [31:0] m_wdata,output reg m_wvalid,input wire m_wready,
 input wire [1:0] m_bresp,input wire m_bvalid,output wire m_bready,
 output reg [8:0] m_araddr,output reg m_arvalid,input wire m_arready,
 input wire [31:0] m_rdata,input wire [1:0] m_rresp,input wire m_rvalid,output wire m_rready
);
 reg [31:0] regs[0:63];
 reg awfull,wfull;
 reg [8:0] awsaved;
 reg [31:0] wsaved;
 reg [1:0] wstate,rstate;
 reg legal_config;
 // Configuration history survives the runtime reset that clears enable.
 // Make the resulting quarantine visible without requiring another write.
 wire reset_invalid=prior_armed && !enable;
 integer i,j;
 assign generation={regs[7],regs[6],regs[5],regs[4]};
 assign base0=regs[12];assign base1=regs[13];assign base2=regs[14];assign base3=regs[15];
 assign req_seq={regs[9],regs[8]};assign req_slot=regs[10][1:0];
 assign consume_seq={regs[25],regs[24]};
 assign s_awready=!awfull && wstate==0 && !s_bvalid;
 assign s_wready=!wfull && wstate==0 && !s_bvalid;
 assign s_arready=rstate==0 && !s_rvalid;
 assign m_bready=wstate==2 && !s_bvalid;
 assign m_rready=rstate==2 && !s_rvalid;
 // Two complete configuration stages. SESSION still executes on its original edge.
 reg [31:0] cfg_base_s1[0:3];
 reg [32:0] cfg_end_s1[0:3];
 reg [3:0] cfg_bad_s1,cfg_bad_s2;
 reg cfg_gen_s1,cfg_gen_s2;
 reg [5:0] cfg_overlap_s2;
 integer ci,cj,cp;
 always @(posedge clk) begin
  if(!resetn) begin
   cfg_bad_s1<=0;cfg_bad_s2<=0;cfg_gen_s1<=0;cfg_gen_s2<=0;cfg_overlap_s2<=0;
   for(ci=0;ci<4;ci=ci+1)begin cfg_base_s1[ci]<=0;cfg_end_s1[ci]<=0;end
  end else begin
   for(ci=0;ci<4;ci=ci+1)begin
    cfg_base_s1[ci]<=regs[12+ci];
    cfg_end_s1[ci]<={1'b0,regs[12+ci]}+33'd2764800;
    cfg_bad_s1[ci]<=(regs[12+ci][11:0]!=0 || regs[12+ci]>32'h20000000-2764800);
   end
   cfg_gen_s1<=(generation!=0);
   cfg_bad_s2<=cfg_bad_s1;cfg_gen_s2<=cfg_gen_s1;
   cp=0;
   for(ci=0;ci<4;ci=ci+1)for(cj=ci+1;cj<4;cj=cj+1)begin
    cfg_overlap_s2[cp]<=!(cfg_end_s1[ci]<={1'b0,cfg_base_s1[cj]} || cfg_end_s1[cj]<={1'b0,cfg_base_s1[ci]});
    cp=cp+1;
   end
  end
 end
 always @* begin
  legal_config=cfg_gen_s2;
  for(integer n=0;n<4;n=n+1)if(cfg_bad_s2[n])legal_config=0;
  for(integer n=0;n<6;n=n+1)if(cfg_overlap_s2[n])legal_config=0;
 end
 always @(posedge clk) begin
  if(!resetn) begin
   enable<=0;req<=0;consume<=0;protocol_error<=0;
   awfull<=0;wfull<=0;awsaved<=0;wsaved<=0;wstate<=0;rstate<=0;
   s_bresp<=0;s_bvalid<=0;s_rdata<=0;s_rresp<=0;s_rvalid<=0;
   m_awaddr<=0;m_awvalid<=0;m_wdata<=0;m_wvalid<=0;m_araddr<=0;m_arvalid<=0;
   for(i=0;i<64;i=i+1)regs[i]<=0;
  end else begin
   req<=0;consume<=0;
   if(s_bvalid && s_bready)s_bvalid<=0;
   if(s_rvalid && s_rready)s_rvalid<=0;
   if(s_awready && s_awvalid)begin awsaved<=s_awaddr;awfull<=1;end
   if(s_wready && s_wvalid)begin wsaved<=s_wdata;wfull<=1;end
   if(wstate==0 && awfull && wfull && !s_bvalid)begin
    awfull<=0;wfull<=0;
    if(awsaved[8])begin
     s_bvalid<=1;s_bresp<=0;
     if(awsaved[1:0]!=0)begin s_bresp<=2;protocol_error<=1;end
     else case(awsaved[7:2])
      3:begin // SESSION arm; cold before any frame, never re-arm after a reset without a new proven bus session.
       if(wsaved!=1 || enable || prior_armed || engine_seen || protocol_error || fence_error || !legal_config)begin s_bresp<=2;protocol_error<=1;end
       else enable<=1;
      end
      4,5,6,7,12,13,14,15:begin
       if(enable || engine_seen)begin s_bresp<=2;protocol_error<=1;end
       else regs[awsaved[7:2]]<=wsaved;
      end
      8,9,10,32,33,34,35:begin // submission and explicit generation echo
       if(busy || req)begin s_bresp<=2;protocol_error<=1;end
       else regs[awsaved[7:2]]<=wsaved;
      end
      11:begin
       if(!enable || wsaved!=1 || {regs[35],regs[34],regs[33],regs[32]}!=generation || regs[10]>3 || fence_error || protocol_error)begin s_bresp<=2;protocol_error<=1;end
       else req<=1;
      end
      24,25,28,29,30,31:regs[awsaved[7:2]]<=wsaved;
      26:begin
       if(!enable || wsaved!=1 || {regs[31],regs[30],regs[29],regs[28]}!=generation)begin s_bresp<=2;protocol_error<=1;end
       else consume<=1;
      end
      default:begin s_bresp<=2;protocol_error<=1;end
     endcase
    end else if((prior_armed && !enable) || protocol_error || fence_error || (enable && started))begin s_bvalid<=1;s_bresp<=2;protocol_error<=1;end
    else begin
     m_awaddr<=awsaved;m_awvalid<=1;m_wdata<=wsaved;m_wvalid<=1;wstate<=1;
    end
   end
   if(wstate==1)begin
    if(m_awvalid && m_awready)m_awvalid<=0;
    if(m_wvalid && m_wready)m_wvalid<=0;
    if((!m_awvalid || m_awready) && (!m_wvalid || m_wready))wstate<=2;
   end
   if(m_bvalid && m_bready)begin s_bvalid<=1;s_bresp<=m_bresp;wstate<=0;end
   if(s_arvalid && s_arready)begin
    if(s_araddr[8])begin
     s_rvalid<=1;s_rresp<=0;s_rdata<=0;
     if(s_araddr[1:0]!=0)s_rresp<=2;
     else case(s_araddr[7:2])
      0:s_rdata<=32'h46520101;
      1:s_rdata<={26'b0,reset_invalid|protocol_error|(|fence_error),retire_valid,accepted,busy,started,enable};
      2:s_rdata<=fence_error|{31'b0,protocol_error}|(reset_invalid?32'h400:32'b0);
      16:s_rdata<=accepted_seq[31:0];17:s_rdata<=accepted_seq[63:32];
      18:s_rdata<=retire_seq[31:0];19:s_rdata<=retire_seq[63:32];
      20:s_rdata<={30'b0,retire_slot};21:s_rdata<={30'b0,active_slot};
      default:s_rdata<=regs[s_araddr[7:2]];
     endcase
    end else begin m_araddr<=s_araddr;m_arvalid<=1;rstate<=1;end
   end
   if(rstate==1 && m_arvalid && m_arready)begin m_arvalid<=0;rstate<=2;end
   if(m_rvalid && m_rready)begin s_rvalid<=1;s_rdata<=m_rdata;s_rresp<=m_rresp;rstate<=0;end
  end
 end
endmodule
