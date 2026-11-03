`timescale 1ns/1ps
// Shared-clock Lab07 integration. AXI reset never enters Main.
module lab07_d_main_top #(parameter ROM_FILE="hann_q17.hex")(
 input wire [31:0] raw_axi_awaddr,raw_axi_wdata,raw_axi_araddr,
 input wire [2:0] raw_axi_awprot,raw_axi_arprot,
 input wire [3:0] raw_axi_wstrb,
 input wire raw_axi_awvalid,raw_axi_wvalid,raw_axi_bready,raw_axi_arvalid,raw_axi_rready,
 output wire raw_axi_awready,raw_axi_wready,raw_axi_bvalid,raw_axi_arready,raw_axi_rvalid,
 output wire [31:0] raw_axi_rdata,
 output wire [1:0] raw_axi_bresp,raw_axi_rresp,
 input wire clk_125mhz,
 input wire [15:0] ad_data,
 input wire ad_busy,ad_frstdata,
 output wire ad_convst,ad_reset,ad_cs_n,ad_rd_n,
  input wire s_axi_aresetn,
 input wire [31:0] s_axi_awaddr,
 input wire [2:0] s_axi_awprot,
 input wire s_axi_awvalid,
 output wire s_axi_awready,
 input wire [31:0] s_axi_wdata,
 input wire [3:0] s_axi_wstrb,
 input wire s_axi_wvalid,
 output wire s_axi_wready,
 output wire [1:0] s_axi_bresp,
 output wire s_axi_bvalid,
 input wire s_axi_bready,
 input wire [31:0] s_axi_araddr,
 input wire [2:0] s_axi_arprot,
 input wire s_axi_arvalid,
 output wire s_axi_arready,
 output wire [31:0] s_axi_rdata,
 output wire [1:0] s_axi_rresp,
 output wire s_axi_rvalid,
 input wire s_axi_rready
);
  wire sample_valid;
 wire [10:0] sample_index;
 wire [31:0] sample_frame_id;
 wire [15:0] sample_ch1_code;
 wire [15:0] sample_ch2_code;
 wire [1:0] sample_channel_valid;
 wire sample_abort;
 wire feature_snapshot_valid;
 wire [31:0] feature_snapshot_seq;
 wire [31:0] feature_frame_id;
 wire [8:0] feature_valid_mask;
 wire feature_acquisition_valid;
 wire [7:0] feature_time_status;
 wire [31:0] feature_spectral_status;
 wire [31:0] feature_numeric_status;
 wire [3:0] feature_formal_identity;
 wire [15:0] ch1_rms;
 wire [15:0] ch2_rms;
 wire [15:0] ch1_peak;
 wire [15:0] ch2_peak;
 wire [15:0] ch1_crest;
 wire [15:0] ch2_crest;
 wire [31:0] frequency_ch1_mhz;
 wire [31:0] ch1_h1;
 wire [31:0] ch1_h3;
 wire [31:0] ch1_h5;
 wire [31:0] ch1_h7;
 wire [31:0] ch1_h9;
 wire [31:0] ch2_h1;
 wire [31:0] ch2_h3;
 wire [31:0] ch2_h5;
 wire [31:0] ch2_h7;
 wire [31:0] ch2_h9;
 wire [31:0] ch1_thd;
 wire [31:0] ch2_thd;
 wire acquisition_fault_live;
 wire [7:0] acquisition_fault_code_live;
 wire branch_mismatch_sticky;
 wire order_unknown_sticky;
 wire [31:0] last_mismatch_time_id;
 wire [31:0] last_mismatch_spectral_id;
 wire time_waiting_for_spectral;
 wire spectral_waiting_for_time;
 wire time_output_held;
 wire spectral_output_held;
 wire lab05_summary_overrun_live;
 wire lab05_result_overrun_live;
 wire lab06_bank_overrun_sticky;
 wire lab06_frame_error_sticky;
 wire lab06_protocol_error_sticky;
 wire [31:0] last_successful_feature_frame_id;
 wire [31:0] snapshot_update_counter;
 wire raw_ack_valid,raw_ack_bank_id,raw_read_en,raw_read_bank_id;
 wire [31:0] raw_ack_token;
 wire [10:0] raw_read_index;
 wire raw_read_busy,raw_read_start,ack_reservation;
 wire [31:0] raw_read_data;
 wire raw_read_valid;
 wire raw_frame_valid;
 wire raw_bank_id;
 wire [31:0] raw_frame_id;
 wire [7:0] raw_status;
 wire [31:0] raw_owner_token;
 wire raw_drop_sticky;
 wire [31:0] raw_drop_count;
 wire raw_protocol_sticky;
 wire raw_ack_error_sticky;
 wire raw_token_exhausted_sticky;
 wire [7:0] raw_bank_states;
 lab07_main #(.ROM_FILE(ROM_FILE)) u_main(.ad_convst(ad_convst),
  .ad_reset(ad_reset),
  .ad_cs_n(ad_cs_n),
  .ad_rd_n(ad_rd_n),
  .sample_valid(sample_valid),
  .sample_index(sample_index),
  .sample_frame_id(sample_frame_id),
  .sample_ch1_code(sample_ch1_code),
  .sample_ch2_code(sample_ch2_code),
  .sample_channel_valid(sample_channel_valid),
  .sample_abort(sample_abort),
  .feature_snapshot_valid(feature_snapshot_valid),
  .feature_snapshot_seq(feature_snapshot_seq),
  .feature_frame_id(feature_frame_id),
  .feature_valid_mask(feature_valid_mask),
  .feature_acquisition_valid(feature_acquisition_valid),
  .feature_time_status(feature_time_status),
  .feature_spectral_status(feature_spectral_status),
  .feature_numeric_status(feature_numeric_status),
  .feature_formal_identity(feature_formal_identity),
  .ch1_rms(ch1_rms),
  .ch2_rms(ch2_rms),
  .ch1_peak(ch1_peak),
  .ch2_peak(ch2_peak),
  .ch1_crest(ch1_crest),
  .ch2_crest(ch2_crest),
  .frequency_ch1_mhz(frequency_ch1_mhz),
  .ch1_h1(ch1_h1),
  .ch1_h3(ch1_h3),
  .ch1_h5(ch1_h5),
  .ch1_h7(ch1_h7),
  .ch1_h9(ch1_h9),
  .ch2_h1(ch2_h1),
  .ch2_h3(ch2_h3),
  .ch2_h5(ch2_h5),
  .ch2_h7(ch2_h7),
  .ch2_h9(ch2_h9),
  .ch1_thd(ch1_thd),
  .ch2_thd(ch2_thd),
  .acquisition_fault_live(acquisition_fault_live),
  .acquisition_fault_code_live(acquisition_fault_code_live),
  .branch_mismatch_sticky(branch_mismatch_sticky),
  .order_unknown_sticky(order_unknown_sticky),
  .last_mismatch_time_id(last_mismatch_time_id),
  .last_mismatch_spectral_id(last_mismatch_spectral_id),
  .time_waiting_for_spectral(time_waiting_for_spectral),
  .spectral_waiting_for_time(spectral_waiting_for_time),
  .time_output_held(time_output_held),
  .spectral_output_held(spectral_output_held),
  .lab05_summary_overrun_live(lab05_summary_overrun_live),
  .lab05_result_overrun_live(lab05_result_overrun_live),
  .lab06_bank_overrun_sticky(lab06_bank_overrun_sticky),
  .lab06_frame_error_sticky(lab06_frame_error_sticky),
  .lab06_protocol_error_sticky(lab06_protocol_error_sticky),
  .last_successful_feature_frame_id(last_successful_feature_frame_id),
  .snapshot_update_counter(snapshot_update_counter),
  .raw_read_data(raw_read_data),
  .raw_read_valid(raw_read_valid),
  .raw_frame_valid(raw_frame_valid),
  .raw_bank_id(raw_bank_id),
  .raw_frame_id(raw_frame_id),
  .raw_status(raw_status),
  .raw_owner_token(raw_owner_token),
  .raw_drop_sticky(raw_drop_sticky),
  .raw_drop_count(raw_drop_count),
  .raw_protocol_sticky(raw_protocol_sticky),
  .raw_ack_error_sticky(raw_ack_error_sticky),
  .raw_token_exhausted_sticky(raw_token_exhausted_sticky),
  .raw_bank_states(raw_bank_states),
  .clk_125mhz(clk_125mhz),
  .ad_data(ad_data),
  .ad_busy(ad_busy),
  .ad_frstdata(ad_frstdata),
  .raw_ack_valid(raw_ack_valid),
  .raw_ack_bank_id(raw_ack_bank_id),
  .raw_ack_token(raw_ack_token),
  .raw_read_en(raw_read_en),
  .raw_read_bank_id(raw_read_bank_id),
  .raw_read_index(raw_read_index));
 lab07_d_feature_slave u_axi(
 .main_reset(ad_reset),.raw_frame_valid(raw_frame_valid),.raw_bank_id(raw_bank_id),
 .raw_frame_id(raw_frame_id),.raw_owner_token(raw_owner_token),.raw_status(raw_status),
 .raw_bank_states(raw_bank_states),.raw_read_busy(raw_read_busy),.raw_read_start(raw_read_start),
 .ack_reservation(ack_reservation),.raw_ack_valid(raw_ack_valid),
 .raw_ack_bank_id(raw_ack_bank_id),.raw_ack_token(raw_ack_token),.s_axi_aclk(clk_125mhz),
  .s_axi_aresetn(s_axi_aresetn),
  .s_axi_awaddr(s_axi_awaddr),
  .s_axi_awprot(s_axi_awprot),
  .s_axi_awvalid(s_axi_awvalid),
  .s_axi_awready(s_axi_awready),
  .s_axi_wdata(s_axi_wdata),
  .s_axi_wstrb(s_axi_wstrb),
  .s_axi_wvalid(s_axi_wvalid),
  .s_axi_wready(s_axi_wready),
  .s_axi_bresp(s_axi_bresp),
  .s_axi_bvalid(s_axi_bvalid),
  .s_axi_bready(s_axi_bready),
  .s_axi_araddr(s_axi_araddr),
  .s_axi_arprot(s_axi_arprot),
  .s_axi_arvalid(s_axi_arvalid),
  .s_axi_arready(s_axi_arready),
  .s_axi_rdata(s_axi_rdata),
  .s_axi_rresp(s_axi_rresp),
  .s_axi_rvalid(s_axi_rvalid),
  .s_axi_rready(s_axi_rready),
  .feature_snapshot_seq(feature_snapshot_seq),
  .feature_snapshot_valid(feature_snapshot_valid),
  .feature_frame_id(feature_frame_id),
  .feature_valid_mask(feature_valid_mask),
  .feature_acquisition_valid(feature_acquisition_valid),
  .feature_time_status(feature_time_status),
  .feature_spectral_status(feature_spectral_status),
  .feature_numeric_status(feature_numeric_status),
  .feature_formal_identity(feature_formal_identity),
  .ch1_rms(ch1_rms),
  .ch1_peak(ch1_peak),
  .ch1_crest(ch1_crest),
  .frequency_ch1_mhz(frequency_ch1_mhz),
  .ch1_h1(ch1_h1),
  .ch1_h3(ch1_h3),
  .ch1_h5(ch1_h5),
  .ch1_h7(ch1_h7),
  .ch1_h9(ch1_h9),
  .ch1_thd(ch1_thd),
  .ch2_rms(ch2_rms),
  .ch2_peak(ch2_peak),
  .ch2_crest(ch2_crest),
  .ch2_h1(ch2_h1),
  .ch2_h3(ch2_h3),
  .ch2_h5(ch2_h5),
  .ch2_h7(ch2_h7),
  .ch2_h9(ch2_h9),
  .ch2_thd(ch2_thd),
  .acquisition_fault_live(acquisition_fault_live),
  .acquisition_fault_code_live(acquisition_fault_code_live),
  .branch_mismatch_sticky(branch_mismatch_sticky),
  .order_unknown_sticky(order_unknown_sticky),
  .last_mismatch_time_id(last_mismatch_time_id),
  .last_mismatch_spectral_id(last_mismatch_spectral_id),
  .time_waiting_for_spectral(time_waiting_for_spectral),
  .spectral_waiting_for_time(spectral_waiting_for_time),
  .time_output_held(time_output_held),
  .spectral_output_held(spectral_output_held),
  .lab05_summary_overrun_live(lab05_summary_overrun_live),
  .lab05_result_overrun_live(lab05_result_overrun_live),
  .lab06_bank_overrun_sticky(lab06_bank_overrun_sticky),
  .lab06_frame_error_sticky(lab06_frame_error_sticky),
  .lab06_protocol_error_sticky(lab06_protocol_error_sticky),
  .last_successful_feature_frame_id(last_successful_feature_frame_id),
  .snapshot_update_counter(snapshot_update_counter),
  .raw_drop_sticky(raw_drop_sticky),
  .raw_drop_count(raw_drop_count),
  .raw_protocol_sticky(raw_protocol_sticky),
  .raw_ack_error_sticky(raw_ack_error_sticky),
  .raw_token_exhausted_sticky(raw_token_exhausted_sticky));
 lab07_raw_memory_bridge u_raw_bridge(
 .clk(clk_125mhz),.aresetn(s_axi_aresetn),.main_reset(ad_reset),
 .owner_valid(raw_frame_valid),.owner_bank(raw_bank_id),.owner_fid(raw_frame_id),
 .owner_token(raw_owner_token),.owner_status(raw_status),.ack_reservation(ack_reservation),
 .read_busy(raw_read_busy),.read_start(raw_read_start),
 .raw_read_en(raw_read_en),.raw_read_bank_id(raw_read_bank_id),.raw_read_index(raw_read_index),
 .raw_read_valid(raw_read_valid),.raw_read_data(raw_read_data),
 .s_axi_awaddr(raw_axi_awaddr),.s_axi_awprot(raw_axi_awprot),.s_axi_awvalid(raw_axi_awvalid),.s_axi_awready(raw_axi_awready),
 .s_axi_wdata(raw_axi_wdata),.s_axi_wstrb(raw_axi_wstrb),.s_axi_wvalid(raw_axi_wvalid),.s_axi_wready(raw_axi_wready),
 .s_axi_bresp(raw_axi_bresp),.s_axi_bvalid(raw_axi_bvalid),.s_axi_bready(raw_axi_bready),
 .s_axi_araddr(raw_axi_araddr),.s_axi_arprot(raw_axi_arprot),.s_axi_arvalid(raw_axi_arvalid),.s_axi_arready(raw_axi_arready),
 .s_axi_rdata(raw_axi_rdata),.s_axi_rresp(raw_axi_rresp),.s_axi_rvalid(raw_axi_rvalid),.s_axi_rready(raw_axi_rready));
endmodule
