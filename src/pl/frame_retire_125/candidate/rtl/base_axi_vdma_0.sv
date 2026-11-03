module base_axi_vdma_0 #(parameter integer RETIRE_HEIGHT=720)(
input wire s_axi_lite_aclk,
input wire m_axi_mm2s_aclk,
input wire m_axis_mm2s_aclk,
input wire axi_resetn,
input wire retire_video_resetn,
input wire s_axi_lite_awvalid,
output wire s_axi_lite_awready,
input wire [8:0] s_axi_lite_awaddr,
input wire s_axi_lite_wvalid,
output wire s_axi_lite_wready,
input wire [31:0] s_axi_lite_wdata,
output wire [1:0] s_axi_lite_bresp,
output wire s_axi_lite_bvalid,
input wire s_axi_lite_bready,
input wire s_axi_lite_arvalid,
output wire s_axi_lite_arready,
input wire [8:0] s_axi_lite_araddr,
output wire s_axi_lite_rvalid,
input wire s_axi_lite_rready,
output wire [31:0] s_axi_lite_rdata,
output wire [1:0] s_axi_lite_rresp,
input wire [5:0] mm2s_frame_ptr_in,
output wire [5:0] mm2s_frame_ptr_out,
output wire [31:0] m_axi_mm2s_araddr,
output wire [7:0] m_axi_mm2s_arlen,
output wire [2:0] m_axi_mm2s_arsize,
output wire [1:0] m_axi_mm2s_arburst,
output wire [2:0] m_axi_mm2s_arprot,
output wire [3:0] m_axi_mm2s_arcache,
output wire m_axi_mm2s_arvalid,
input wire m_axi_mm2s_arready,
input wire [31:0] m_axi_mm2s_rdata,
input wire [1:0] m_axi_mm2s_rresp,
input wire m_axi_mm2s_rlast,
input wire m_axi_mm2s_rvalid,
output wire m_axi_mm2s_rready,
output wire [31:0] m_axis_mm2s_tdata,
output wire [3:0] m_axis_mm2s_tkeep,
output wire [0:0] m_axis_mm2s_tuser,
output wire m_axis_mm2s_tvalid,
input wire m_axis_mm2s_tready,
output wire m_axis_mm2s_tlast,
output wire mm2s_introut
);
`ifdef SYNTHESIS
// Scaled height is a simulation-only verification aid; shipping geometry fixed.
initial begin if(RETIRE_HEIGHT!=720)$error("Synthesized retire geometry must be 720p");end
`endif
wire core_awvalid;
wire core_awready;
wire [8:0] core_awaddr;
wire core_wvalid;
wire core_wready;
wire [31:0] core_wdata;
wire [1:0] core_bresp;
wire core_bvalid;
wire core_bready;
wire core_arvalid;
wire core_arready;
wire [8:0] core_araddr;
wire core_rvalid;
wire core_rready;
wire [31:0] core_rdata;
wire [1:0] core_rresp;
wire core_resetn, control_resetn;
wire [31:0] memory_rdata;
wire [1:0] memory_rresp;
wire memory_rlast, memory_rvalid, memory_rready;
vdma_mm2s_r_slice memory_r_slice (
 .clk(m_axi_mm2s_aclk),.resetn(core_resetn),
 .s_rdata(m_axi_mm2s_rdata),.s_rresp(m_axi_mm2s_rresp),
 .s_rlast(m_axi_mm2s_rlast),.s_rvalid(m_axi_mm2s_rvalid),.s_rready(m_axi_mm2s_rready),
 .m_rdata(memory_rdata),.m_rresp(memory_rresp),
 .m_rlast(memory_rlast),.m_rvalid(memory_rvalid),.m_rready(memory_rready));

(* KEEP="TRUE" *) wire core_irq;
(* ASYNC_REG="TRUE" *) reg [1:0] irq_level;
always @(posedge s_axi_lite_aclk or negedge control_resetn)
 if(!control_resetn) irq_level<=0;
 else if(!control_resetn) irq_level<=0;
 else irq_level<={irq_level[0],core_irq};
assign mm2s_introut=irq_level[1];
vdma_axil_snapshot_bridge bridge(.s_aclk(s_axi_lite_aclk),.m_aclk(m_axi_mm2s_aclk),.resetn(axi_resetn),.s_resetn_out(control_resetn),.m_resetn_out(core_resetn),
.s_axi_awvalid(s_axi_lite_awvalid),
.m_axi_awvalid(core_awvalid),
.s_axi_awready(s_axi_lite_awready),
.m_axi_awready(core_awready),
.s_axi_awaddr(s_axi_lite_awaddr),
.m_axi_awaddr(core_awaddr),
.s_axi_wvalid(s_axi_lite_wvalid),
.m_axi_wvalid(core_wvalid),
.s_axi_wready(s_axi_lite_wready),
.m_axi_wready(core_wready),
.s_axi_wdata(s_axi_lite_wdata),
.m_axi_wdata(core_wdata),
.s_axi_bresp(s_axi_lite_bresp),
.m_axi_bresp(core_bresp),
.s_axi_bvalid(s_axi_lite_bvalid),
.m_axi_bvalid(core_bvalid),
.s_axi_bready(s_axi_lite_bready),
.m_axi_bready(core_bready),
.s_axi_arvalid(s_axi_lite_arvalid),
.m_axi_arvalid(core_arvalid),
.s_axi_arready(s_axi_lite_arready),
.m_axi_arready(core_arready),
.s_axi_araddr(s_axi_lite_araddr),
.m_axi_araddr(core_araddr),
.s_axi_rvalid(s_axi_lite_rvalid),
.m_axi_rvalid(core_rvalid),
.s_axi_rready(s_axi_lite_rready),
.m_axi_rready(core_rready),
.s_axi_rdata(s_axi_lite_rdata),
.m_axi_rdata(core_rdata),
.s_axi_rresp(s_axi_lite_rresp),
.m_axi_rresp(core_rresp));
wire vendor_awvalid;
wire vendor_awready;
wire [8:0] vendor_awaddr;
wire vendor_wvalid;
wire vendor_wready;
wire [31:0] vendor_wdata;
wire [1:0] vendor_bresp;
wire vendor_bvalid;
wire vendor_bready;
wire vendor_arvalid;
wire vendor_arready;
wire [8:0] vendor_araddr;
wire vendor_rvalid;
wire vendor_rready;
wire [31:0] vendor_rdata;
wire [1:0] vendor_rresp;
wire retire_enable,req,consume,protocol_error;
wire [127:0] retire_generation;
wire [31:0] base0,base1,base2,base3,retire_base,fence_error;
wire [63:0] req_seq,consume_seq,accepted_seq,retire_seq;
wire [1:0] req_slot,active_slot,retire_slot;
wire started,busy,accepted,retire_valid;
wire fr_frame_start,fr_command_generate,fr_last_command,fr_geometry_good,fr_abort;
wire fr_dm_accept,fr_status_accept;
wire [7:0] fr_status_data;
reg engine_seen=0;
// FPGA configuration initializes this bit. Deliberately no runtime reset:
// after any reader/control reset a second dynamic arm is forbidden until a
// separately controlled new FPGA/bus session; cleared ledgers are not drains.
reg prior_armed=0;
always @(posedge m_axi_mm2s_aclk) if(retire_enable)prior_armed<=1;
// Static reads also make this configuration ineligible for a later cold arm.
// Clearing the reader/control reset must not erase that history.
always @(posedge m_axi_mm2s_aclk) if(fr_frame_start)engine_seen<=1;
wire [31:0] raw_araddr;
wire [7:0] raw_arlen;
wire [2:0] raw_arsize,raw_arprot;
wire [1:0] raw_arburst;
wire [3:0] raw_arcache;
wire raw_arvalid,raw_arready;
frame_retire_registers retire_registers(
 .clk(m_axi_mm2s_aclk),.resetn(core_resetn),.engine_seen(engine_seen),.prior_armed(prior_armed),
 .started(started),.busy(busy),.accepted(accepted),.retire_valid(retire_valid),
 .accepted_seq(accepted_seq),.retire_seq(retire_seq),.active_slot(active_slot),.retire_slot(retire_slot),
 .fence_error(fence_error),.enable(retire_enable),.req(req),.consume(consume),.protocol_error(protocol_error),
 .generation(retire_generation),.base0(base0),.base1(base1),.base2(base2),.base3(base3),
 .req_seq(req_seq),.consume_seq(consume_seq),.req_slot(req_slot),
 .s_awvalid(core_awvalid),
 .s_awready(core_awready),
 .s_awaddr(core_awaddr),
 .s_wvalid(core_wvalid),
 .s_wready(core_wready),
 .s_wdata(core_wdata),
 .s_bresp(core_bresp),
 .s_bvalid(core_bvalid),
 .s_bready(core_bready),
 .s_arvalid(core_arvalid),
 .s_arready(core_arready),
 .s_araddr(core_araddr),
 .s_rvalid(core_rvalid),
 .s_rready(core_rready),
 .s_rdata(core_rdata),
 .s_rresp(core_rresp),
 .m_awvalid(vendor_awvalid),
 .m_awready(vendor_awready),
 .m_awaddr(vendor_awaddr),
 .m_wvalid(vendor_wvalid),
 .m_wready(vendor_wready),
 .m_wdata(vendor_wdata),
 .m_bresp(vendor_bresp),
 .m_bvalid(vendor_bvalid),
 .m_bready(vendor_bready),
 .m_arvalid(vendor_arvalid),
 .m_arready(vendor_arready),
 .m_araddr(vendor_araddr),
 .m_rvalid(vendor_rvalid),
 .m_rready(vendor_rready),
 .m_rdata(vendor_rdata),
 .m_rresp(vendor_rresp));
frame_retire_fence #(.FRAME_BYTES(3840*RETIRE_HEIGHT)) retire_fence(
 .clk(m_axi_mm2s_aclk),.resetn(core_resetn),.enable(retire_enable),
 .external_fault(protocol_error || (started && (fr_abort || !retire_video_resetn)) || (fr_frame_start && !fr_geometry_good)),
 .generation(retire_generation),.base0(base0),.base1(base1),.base2(base2),.base3(base3),
 .req(req),.consume(consume),.req_seq(req_seq),.consume_seq(consume_seq),.req_slot(req_slot),
 .frame_start(fr_frame_start),.command_generate(fr_command_generate),.last_command(fr_last_command),
 .command_accept(fr_dm_accept),.status_accept(fr_status_accept),.status_data(fr_status_data),
 .core_araddr(raw_araddr),.core_arlen(raw_arlen),.core_arsize(raw_arsize),.core_arburst(raw_arburst),
 .core_arprot(raw_arprot),.core_arcache(raw_arcache),.core_arvalid(raw_arvalid),.core_arready(raw_arready),
 .memory_araddr(m_axi_mm2s_araddr),.memory_arlen(m_axi_mm2s_arlen),.memory_arsize(m_axi_mm2s_arsize),
 .memory_arburst(m_axi_mm2s_arburst),.memory_arprot(m_axi_mm2s_arprot),.memory_arcache(m_axi_mm2s_arcache),
 .memory_arvalid(m_axi_mm2s_arvalid),.memory_arready(m_axi_mm2s_arready),
 .response_valid(memory_rvalid),.response_ready(memory_rready),.response_last(memory_rlast),.response_code(memory_rresp),
 .next_base(retire_base),.active_slot(active_slot),.started(started),.busy(busy),.accepted(accepted),
 .retire_valid(retire_valid),.accepted_seq(accepted_seq),.retire_seq(retire_seq),.retire_slot(retire_slot),.error_status(fence_error));
axi_vdma #(
.C_S_AXI_LITE_ADDR_WIDTH(9),
.C_S_AXI_LITE_DATA_WIDTH(32),
.C_DLYTMR_RESOLUTION(125),
.C_PRMRY_IS_ACLK_ASYNC(0),
.C_ENABLE_VIDPRMTR_READS(1),
.C_DYNAMIC_RESOLUTION(1),
.C_NUM_FSTORES(4),
.C_USE_FSYNC(1),
.C_USE_MM2S_FSYNC(0),
.C_USE_S2MM_FSYNC(2),
.C_FLUSH_ON_FSYNC(1),
.C_INCLUDE_INTERNAL_GENLOCK(1),
.C_INCLUDE_SG(0),
.C_M_AXI_SG_ADDR_WIDTH(32),
.C_M_AXI_SG_DATA_WIDTH(32),
.C_INCLUDE_MM2S(1),
.C_MM2S_GENLOCK_MODE(1),
.C_MM2S_GENLOCK_NUM_MASTERS(1),
.C_MM2S_GENLOCK_REPEAT_EN(0),
.C_MM2S_SOF_ENABLE(1),
.C_INCLUDE_MM2S_DRE(0),
.C_INCLUDE_MM2S_SF(0),
.C_MM2S_LINEBUFFER_DEPTH(512),
.C_MM2S_LINEBUFFER_THRESH(4),
.C_MM2S_MAX_BURST_LENGTH(32),
.C_M_AXI_MM2S_ADDR_WIDTH(32),
.C_M_AXI_MM2S_DATA_WIDTH(32),
.C_M_AXIS_MM2S_TDATA_WIDTH(32),
.C_M_AXIS_MM2S_TUSER_BITS(1),
.C_INCLUDE_S2MM(0),
.C_S2MM_GENLOCK_MODE(0),
.C_S2MM_GENLOCK_NUM_MASTERS(1),
.C_S2MM_GENLOCK_REPEAT_EN(1),
.C_S2MM_SOF_ENABLE(1),
.C_INCLUDE_S2MM_DRE(0),
.C_INCLUDE_S2MM_SF(1),
.C_S2MM_LINEBUFFER_DEPTH(512),
.C_S2MM_LINEBUFFER_THRESH(4),
.C_S2MM_MAX_BURST_LENGTH(8),
.C_M_AXI_S2MM_ADDR_WIDTH(32),
.C_M_AXI_S2MM_DATA_WIDTH(64),
.C_S_AXIS_S2MM_TDATA_WIDTH(32),
.C_S_AXIS_S2MM_TUSER_BITS(1),
.C_ENABLE_DEBUG_ALL(0),
.C_ENABLE_DEBUG_INFO_0(0),
.C_ENABLE_DEBUG_INFO_1(0),
.C_ENABLE_DEBUG_INFO_2(0),
.C_ENABLE_DEBUG_INFO_3(0),
.C_ENABLE_DEBUG_INFO_4(0),
.C_ENABLE_DEBUG_INFO_5(0),
.C_ENABLE_DEBUG_INFO_6(1),
.C_ENABLE_DEBUG_INFO_7(1),
.C_ENABLE_DEBUG_INFO_8(0),
.C_ENABLE_DEBUG_INFO_9(0),
.C_ENABLE_DEBUG_INFO_10(0),
.C_ENABLE_DEBUG_INFO_11(0),
.C_ENABLE_DEBUG_INFO_12(0),
.C_ENABLE_DEBUG_INFO_13(0),
.C_ENABLE_DEBUG_INFO_14(1),
.C_ENABLE_DEBUG_INFO_15(1),
.C_INSTANCE("axi_vdma"),
.C_SELECT_XPM(0),
.C_ENABLE_VERT_FLIP(0),
.C_FAMILY("zynq")
) U0(
.fr_enable(retire_enable),.fr_expected_height(13'(RETIRE_HEIGHT)),.fr_base(retire_base),
.fr_frame_start(fr_frame_start),.fr_command_generate(fr_command_generate),
.fr_last_command(fr_last_command),.fr_geometry_good(fr_geometry_good),.fr_abort(fr_abort),
.fr_dm_accept(fr_dm_accept),.fr_status_accept(fr_status_accept),.fr_status_data(fr_status_data),
.s_axi_lite_aclk(m_axi_mm2s_aclk),
.m_axi_sg_aclk(1'b0),
.m_axi_mm2s_aclk(m_axi_mm2s_aclk),
.m_axis_mm2s_aclk(m_axis_mm2s_aclk),
.m_axi_s2mm_aclk(1'b0),
.s_axis_s2mm_aclk(1'b0),
.axi_resetn(core_resetn),
.s_axi_lite_awvalid(vendor_awvalid),
.s_axi_lite_awready(vendor_awready),
.s_axi_lite_awaddr(vendor_awaddr),
.s_axi_lite_wvalid(vendor_wvalid),
.s_axi_lite_wready(vendor_wready),
.s_axi_lite_wdata(vendor_wdata),
.s_axi_lite_bresp(vendor_bresp),
.s_axi_lite_bvalid(vendor_bvalid),
.s_axi_lite_bready(vendor_bready),
.s_axi_lite_arvalid(vendor_arvalid),
.s_axi_lite_arready(vendor_arready),
.s_axi_lite_araddr(vendor_araddr),
.s_axi_lite_rvalid(vendor_rvalid),
.s_axi_lite_rready(vendor_rready),
.s_axi_lite_rdata(vendor_rdata),
.s_axi_lite_rresp(vendor_rresp),
.mm2s_fsync(1'b0),
.mm2s_frame_ptr_in(mm2s_frame_ptr_in),
.mm2s_frame_ptr_out(mm2s_frame_ptr_out),
.s2mm_fsync(1'b0),
.s2mm_frame_ptr_in('0),
.m_axi_sg_arready(1'b0),
.m_axi_sg_rdata('0),
.m_axi_sg_rresp('0),
.m_axi_sg_rlast(1'b0),
.m_axi_sg_rvalid(1'b0),
.m_axi_mm2s_araddr(raw_araddr),
.m_axi_mm2s_arlen(raw_arlen),
.m_axi_mm2s_arsize(raw_arsize),
.m_axi_mm2s_arburst(raw_arburst),
.m_axi_mm2s_arprot(raw_arprot),
.m_axi_mm2s_arcache(raw_arcache),
.m_axi_mm2s_arvalid(raw_arvalid),
.m_axi_mm2s_arready(raw_arready),
.m_axi_mm2s_rdata(memory_rdata),
.m_axi_mm2s_rresp(memory_rresp),
.m_axi_mm2s_rlast(memory_rlast),
.m_axi_mm2s_rvalid(memory_rvalid),
.m_axi_mm2s_rready(memory_rready),
.m_axis_mm2s_tdata(m_axis_mm2s_tdata),
.m_axis_mm2s_tkeep(m_axis_mm2s_tkeep),
.m_axis_mm2s_tuser(m_axis_mm2s_tuser),
.m_axis_mm2s_tvalid(m_axis_mm2s_tvalid),
.m_axis_mm2s_tready(m_axis_mm2s_tready),
.m_axis_mm2s_tlast(m_axis_mm2s_tlast),
.m_axi_s2mm_awready(1'b0),
.m_axi_s2mm_wready(1'b0),
.m_axi_s2mm_bresp('0),
.m_axi_s2mm_bvalid(1'b0),
.s_axis_s2mm_tdata('0),
.s_axis_s2mm_tkeep(4'hF),
.s_axis_s2mm_tuser('0),
.s_axis_s2mm_tvalid(1'b0),
.s_axis_s2mm_tlast(1'b0),
.mm2s_introut(core_irq));
endmodule
