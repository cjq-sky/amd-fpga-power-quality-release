`timescale 1ns/1ps
// ABI 2.1 feature/control variant. ACLK MUST be the same physical BUFG output as Main.
module lab07_d_feature_slave(
 input wire main_reset,
 input wire raw_frame_valid,raw_bank_id,
 input wire [31:0] raw_frame_id,raw_owner_token,
 input wire [7:0] raw_status,raw_bank_states,
 input wire raw_read_busy,raw_read_start,
 output wire ack_reservation,raw_ack_valid,raw_ack_bank_id,
 output wire [31:0] raw_ack_token,
 input wire s_axi_aclk,
 input wire s_axi_aresetn,
 input wire [31:0] s_axi_awaddr,
 input wire [2:0] s_axi_awprot,
 input wire s_axi_awvalid,
 output wire s_axi_awready,
 input wire [31:0] s_axi_wdata,
 input wire [3:0] s_axi_wstrb,
 input wire s_axi_wvalid,
 output wire s_axi_wready,
 output reg [1:0] s_axi_bresp,
 output reg s_axi_bvalid,
 input wire s_axi_bready,
 input wire [31:0] s_axi_araddr,
 input wire [2:0] s_axi_arprot,
 input wire s_axi_arvalid,
 output wire s_axi_arready,
 output reg [31:0] s_axi_rdata,
 output reg [1:0] s_axi_rresp,
 output reg s_axi_rvalid,
 input wire s_axi_rready,
  input wire [31:0] feature_snapshot_seq,
 input wire feature_snapshot_valid,
 input wire [31:0] feature_frame_id,
 input wire [8:0] feature_valid_mask,
 input wire feature_acquisition_valid,
 input wire [7:0] feature_time_status,
 input wire [31:0] feature_spectral_status,
 input wire [31:0] feature_numeric_status,
 input wire [3:0] feature_formal_identity,
 input wire [15:0] ch1_rms,
 input wire [15:0] ch1_peak,
 input wire [15:0] ch1_crest,
 input wire [31:0] frequency_ch1_mhz,
 input wire [31:0] ch1_h1,
 input wire [31:0] ch1_h3,
 input wire [31:0] ch1_h5,
 input wire [31:0] ch1_h7,
 input wire [31:0] ch1_h9,
 input wire [31:0] ch1_thd,
 input wire [15:0] ch2_rms,
 input wire [15:0] ch2_peak,
 input wire [15:0] ch2_crest,
 input wire [31:0] ch2_h1,
 input wire [31:0] ch2_h3,
 input wire [31:0] ch2_h5,
 input wire [31:0] ch2_h7,
 input wire [31:0] ch2_h9,
 input wire [31:0] ch2_thd,
 input wire acquisition_fault_live,
 input wire [7:0] acquisition_fault_code_live,
 input wire branch_mismatch_sticky,
 input wire order_unknown_sticky,
 input wire [31:0] last_mismatch_time_id,
 input wire [31:0] last_mismatch_spectral_id,
 input wire time_waiting_for_spectral,
 input wire spectral_waiting_for_time,
 input wire time_output_held,
 input wire spectral_output_held,
 input wire lab05_summary_overrun_live,
 input wire lab05_result_overrun_live,
 input wire lab06_bank_overrun_sticky,
 input wire lab06_frame_error_sticky,
 input wire lab06_protocol_error_sticky,
 input wire [31:0] last_successful_feature_frame_id,
 input wire [31:0] snapshot_update_counter,
 input wire raw_drop_sticky,
 input wire [31:0] raw_drop_count,
 input wire raw_protocol_sticky,
 input wire raw_ack_error_sticky,
 input wire raw_token_exhausted_sticky
);
 reg aw_pending, w_pending;
 reg [31:0] awaddr_q,wdata_q;
 reg [3:0] wstrb_q;
 wire write_fire=aw_pending && w_pending && !s_axi_bvalid;
 wire [1:0] control_write_resp;
 wire [31:0] raw_control_data;
 lab07_raw_control u_raw_control(
 .clk(s_axi_aclk),.aresetn(s_axi_aresetn),.main_reset(main_reset),
 .owner_valid(raw_frame_valid),.owner_bank(raw_bank_id),.owner_fid(raw_frame_id),
 .owner_token(raw_owner_token),.owner_status(raw_status),.bank_states(raw_bank_states),
 .read_addr(s_axi_araddr),.read_data(raw_control_data),
 .write_valid(write_fire),.write_addr(awaddr_q),.write_data(wdata_q),.write_strb(wstrb_q),
 .write_resp(control_write_resp),.read_busy(raw_read_busy),.read_start(raw_read_start),
 .ack_reservation(ack_reservation),.raw_ack_valid(raw_ack_valid),
 .raw_ack_bank_id(raw_ack_bank_id),.raw_ack_token(raw_ack_token));
 reg [31:0] decoded_data;
 reg [1:0] decoded_resp;
 // One response slot; replacement on a simultaneous R handshake is legal.
 assign s_axi_arready = s_axi_aresetn && (!s_axi_rvalid || s_axi_rready);
 assign s_axi_awready = s_axi_aresetn && !aw_pending && !s_axi_bvalid;
 assign s_axi_wready = s_axi_aresetn && !w_pending && !s_axi_bvalid;
 always @* begin
  decoded_data=32'd0; decoded_resp=2'b00;
  case(s_axi_araddr)
    32'h00000000: decoded_data = 32'h50514d37; // MAGIC
   32'h00000004: decoded_data = 32'h00070001; // CORE_ID
   32'h00000008: decoded_data = 32'h00020001; // REGMAP_VERSION
   32'h0000000c: decoded_data = 32'h0000017f; // FEATURE_CAPABILITY
   32'h00000010: decoded_data = 32'h0000000f; // RAW_CAPABILITY
   32'h00000014: decoded_data = 32'h1935f2bc; // BASELINE_ID
   32'h00000018: decoded_data = 32'h00000800; // FRAME_SAMPLES
   32'h0000001c: decoded_data = 32'h00002710; // SAMPLE_RATE_NOMINAL_HZ
   32'h00000040: decoded_data = feature_snapshot_seq; // SNAPSHOT_SEQ
   32'h00000044: decoded_data = {31'd0,feature_snapshot_valid}; // SNAPSHOT_VALID
   32'h00000048: decoded_data = feature_frame_id; // FRAME_ID
   32'h0000004c: decoded_data = {23'd0,feature_valid_mask}; // FEATURE_VALID_MASK
   32'h00000050: decoded_data = {31'd0,feature_acquisition_valid}; // FEATURE_ACQUISITION_VALID
   32'h00000054: decoded_data = {24'd0,feature_time_status}; // TIME_STATUS
   32'h00000058: decoded_data = feature_spectral_status; // SPECTRAL_STATUS
   32'h0000005c: decoded_data = feature_numeric_status; // SPECTRAL_NUMERIC_STATUS
   32'h00000060: decoded_data = {28'd0,feature_formal_identity}; // FORMAL_IDENTITY
   32'h00000080: decoded_data = {16'd0,ch1_rms}; // CH1_RMS
   32'h00000084: decoded_data = {16'd0,ch1_peak}; // CH1_PEAK
   32'h00000088: decoded_data = {16'd0,ch1_crest}; // CH1_CREST
   32'h0000008c: decoded_data = frequency_ch1_mhz; // CH1_FREQUENCY_MHZ
   32'h00000090: decoded_data = ch1_h1; // CH1_H1
   32'h00000094: decoded_data = ch1_h3; // CH1_H3
   32'h00000098: decoded_data = ch1_h5; // CH1_H5
   32'h0000009c: decoded_data = ch1_h7; // CH1_H7
   32'h000000a0: decoded_data = ch1_h9; // CH1_H9
   32'h000000a4: decoded_data = ch1_thd; // CH1_THD_ODD_3_5_7_9
   32'h000000c0: decoded_data = {16'd0,ch2_rms}; // CH2_RMS
   32'h000000c4: decoded_data = {16'd0,ch2_peak}; // CH2_PEAK
   32'h000000c8: decoded_data = {16'd0,ch2_crest}; // CH2_CREST
   32'h000000cc: decoded_data = ch2_h1; // CH2_H1
   32'h000000d0: decoded_data = ch2_h3; // CH2_H3
   32'h000000d4: decoded_data = ch2_h5; // CH2_H5
   32'h000000d8: decoded_data = ch2_h7; // CH2_H7
   32'h000000dc: decoded_data = ch2_h9; // CH2_H9
   32'h000000e0: decoded_data = ch2_thd; // CH2_THD_ODD_3_5_7_9
   32'h00000100: decoded_data = {31'd0,acquisition_fault_live}; // ACQUISITION_FAULT
   32'h00000104: decoded_data = {24'd0,acquisition_fault_code_live}; // ACQUISITION_FAULT_CODE
   32'h00000108: decoded_data = {31'd0,branch_mismatch_sticky}; // BRANCH_MISMATCH_STICKY
   32'h0000010c: decoded_data = {31'd0,order_unknown_sticky}; // ORDER_UNKNOWN_STICKY
   32'h00000110: decoded_data = last_mismatch_time_id; // LAST_MISMATCH_TIME_ID
   32'h00000114: decoded_data = last_mismatch_spectral_id; // LAST_MISMATCH_SPECTRAL_ID
   32'h00000118: decoded_data = {31'd0,time_waiting_for_spectral}; // TIME_WAITING_FOR_SPECTRAL
   32'h0000011c: decoded_data = {31'd0,spectral_waiting_for_time}; // SPECTRAL_WAITING_FOR_TIME
   32'h00000120: decoded_data = {31'd0,time_output_held}; // TIME_OUTPUT_HELD
   32'h00000124: decoded_data = {31'd0,spectral_output_held}; // SPECTRAL_OUTPUT_HELD
   32'h00000128: decoded_data = {31'd0,lab05_summary_overrun_live}; // LAB05_SUMMARY_OVERRUN
   32'h0000012c: decoded_data = {31'd0,lab05_result_overrun_live}; // LAB05_RESULT_OVERRUN
   32'h00000130: decoded_data = {31'd0,lab06_bank_overrun_sticky}; // LAB06_BANK_OVERRUN_STICKY
   32'h00000134: decoded_data = {31'd0,lab06_frame_error_sticky}; // LAB06_FRAME_ERROR_STICKY
   32'h00000138: decoded_data = {31'd0,lab06_protocol_error_sticky}; // LAB06_PROTOCOL_ERROR_STICKY
   32'h0000013c: decoded_data = last_successful_feature_frame_id; // LAST_SUCCESSFUL_FEATURE_FRAME_ID
   32'h00000140: decoded_data = snapshot_update_counter; // SNAPSHOT_UPDATE_COUNTER
   32'h00000144: decoded_data = {31'd0,raw_drop_sticky}; // RAW_DROP_STICKY
   32'h00000148: decoded_data = raw_drop_count; // RAW_DROP_COUNT
   32'h0000014c: decoded_data = {31'd0,raw_protocol_sticky}; // RAW_PROTOCOL_STICKY
   32'h00000150: decoded_data = {31'd0,raw_ack_error_sticky}; // RAW_ACK_ERROR_STICKY
   32'h00000154: decoded_data = {31'd0,raw_token_exhausted_sticky}; // RAW_TOKEN_EXHAUSTED_STICKY
   32'h00000200: decoded_data = raw_control_data; // RAW_DESCRIPTOR_VALID
   32'h00000204: decoded_data = raw_control_data; // RAW_BANK_ID
   32'h00000208: decoded_data = raw_control_data; // RAW_FRAME_ID
   32'h0000020c: decoded_data = raw_control_data; // RAW_OWNER_TOKEN
   32'h00000210: decoded_data = raw_control_data; // RAW_FRAME_STATUS
   32'h00000214: decoded_data = raw_control_data; // RAW_BANK_STATES
   32'h00000218: decoded_data = raw_control_data; // RAW_COMPLETE_PENDING_MASK
   32'h0000021c: decoded_data = raw_control_data; // RAW_SAMPLE_COUNT
   32'h00000220: decoded_data = raw_control_data; // RAW_CHANNEL_MASK
   32'h00000224: decoded_data = raw_control_data; // RAW_FRAME_BYTES
   32'h00000228: decoded_data = raw_control_data; // RAW_WINDOW_OFFSET
   32'h0000022c: decoded_data = raw_control_data; // RAW_WINDOW_SIZE_BYTES
   32'h00000230: decoded_data = raw_control_data; // RAW_FORMAT
   32'h00000240: decoded_data = raw_control_data; // RAW_ACK_BANK
   32'h00000244: decoded_data = raw_control_data; // RAW_ACK_TOKEN
   32'h00000248: decoded_data = raw_control_data; // RAW_ACK
   32'h0000024c: decoded_data = raw_control_data; // RAW_ACK_RESULT
   32'h00000250: decoded_data = raw_control_data; // RAW_ACK_COMPLETED_TOKEN
   default: decoded_resp=2'b10; // undefined/misaligned: SLVERR
  endcase
 end
 always @(posedge s_axi_aclk) begin
  if(!s_axi_aresetn) begin
   s_axi_rvalid<=0;s_axi_rdata<=0;s_axi_rresp<=0;
   aw_pending<=0;w_pending<=0;s_axi_bvalid<=0;s_axi_bresp<=0;awaddr_q<=0;wdata_q<=0;wstrb_q<=0;
  end else begin
   if(s_axi_arready && s_axi_arvalid) begin
    s_axi_rdata<=decoded_data;s_axi_rresp<=decoded_resp;s_axi_rvalid<=1;
   end else if(s_axi_rvalid && s_axi_rready) s_axi_rvalid<=0;
   // Only operational raw staging/command writes are allowed; other writes SLVERR.
   // Independent handshake tokens pair exactly one AW with one W.
   if(s_axi_awready && s_axi_awvalid) begin aw_pending<=1;awaddr_q<=s_axi_awaddr;end
   if(s_axi_wready && s_axi_wvalid) begin w_pending<=1;wdata_q<=s_axi_wdata;wstrb_q<=s_axi_wstrb;end
   if(aw_pending && w_pending && !s_axi_bvalid) begin
    aw_pending<=0;w_pending<=0;s_axi_bvalid<=1;s_axi_bresp<=control_write_resp;
   end else if(s_axi_bvalid && s_axi_bready) s_axi_bvalid<=0;
  end
 end
endmodule
