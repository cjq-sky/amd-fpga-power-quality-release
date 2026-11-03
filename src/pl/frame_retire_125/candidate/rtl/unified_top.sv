`timescale 1ns/1ps
// Release-style Zynq + unchanged Lab07 Main. No ILA/VIO/debug_hub.
module unified_top(
 inout wire [14:0] DDR_0_addr,
 inout wire [2:0] DDR_0_ba,
 inout wire DDR_0_cas_n,
 inout wire DDR_0_ck_n,
 inout wire DDR_0_ck_p,
 inout wire DDR_0_cke,
 inout wire DDR_0_cs_n,
 inout wire [3:0] DDR_0_dm,
 inout wire [31:0] DDR_0_dq,
 inout wire [3:0] DDR_0_dqs_n,
 inout wire [3:0] DDR_0_dqs_p,
 inout wire DDR_0_odt,
 inout wire DDR_0_ras_n,
 inout wire DDR_0_reset_n,
 inout wire DDR_0_we_n,
 inout wire FIXED_IO_0_ddr_vrn,
 inout wire FIXED_IO_0_ddr_vrp,
 inout wire [53:0] FIXED_IO_0_mio,
 inout wire FIXED_IO_0_ps_clk,
 inout wire FIXED_IO_0_ps_porb,
 inout wire FIXED_IO_0_ps_srstb,
 input wire clk_125mhz,
 input wire [15:0] ad_data,
 input wire ad_busy,ad_frstdata,
 output wire ad_convst,ad_reset,ad_cs_n,ad_rd_n,
 output wire led0,
 output wire hdmi_out_clk_n,hdmi_out_clk_p,
 output wire [2:0] hdmi_out_data_n,hdmi_out_data_p,
 input wire [0:0] hdmi_out_hpd
);
 wire clk_ibuf,clk_shared;
 IBUF u_h16_ibuf(.I(clk_125mhz),.O(clk_ibuf));
 BUFG u_h16_bufg(.I(clk_ibuf),.O(clk_shared));
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
 wire  raw_ack_valid;
 wire  raw_ack_bank_id;
 wire [31:0] raw_ack_token;
 wire  raw_read_en;
 wire  raw_read_bank_id;
 wire [10:0] raw_read_index;
 assign led0=feature_snapshot_seq[0];
 lab07_main #(.ROM_FILE("fft_ip/hann_q17.hex")) u_main(
  .ad_convst(ad_convst),
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
  .clk_125mhz(clk_shared),
  .ad_data(ad_data),
  .ad_busy(ad_busy),
  .ad_frstdata(ad_frstdata),
  .raw_ack_valid(raw_ack_valid),
  .raw_ack_bank_id(raw_ack_bank_id),
  .raw_ack_token(raw_ack_token),
  .raw_read_en(raw_read_en),
  .raw_read_bank_id(raw_read_bank_id),
  .raw_read_index(raw_read_index));
 wire hpd_sync_clk_100m;
 wire [0:0] hpd_sync_resetn,hdmi_out_hpd_sync;
 hdmi_hpd_sync hpd_sync(.clk(hpd_sync_clk_100m),.resetn(hpd_sync_resetn[0]),.hpdn_async(hdmi_out_hpd[0]),.hpdn_sync(hdmi_out_hpd_sync[0]));
 base_wrapper base_wrapper_i(
  .hdmi_out_clk_n(hdmi_out_clk_n),.hdmi_out_clk_p(hdmi_out_clk_p),
  .hdmi_out_data_n(hdmi_out_data_n),.hdmi_out_data_p(hdmi_out_data_p),
  .hdmi_out_hpd_sync(hdmi_out_hpd_sync),.hpd_sync_clk_100m(hpd_sync_clk_100m),.hpd_sync_resetn(hpd_sync_resetn),
  .DDR_addr(DDR_0_addr),
  .DDR_ba(DDR_0_ba),
  .DDR_cas_n(DDR_0_cas_n),
  .DDR_ck_n(DDR_0_ck_n),
  .DDR_ck_p(DDR_0_ck_p),
  .DDR_cke(DDR_0_cke),
  .DDR_cs_n(DDR_0_cs_n),
  .DDR_dm(DDR_0_dm),
  .DDR_dq(DDR_0_dq),
  .DDR_dqs_n(DDR_0_dqs_n),
  .DDR_dqs_p(DDR_0_dqs_p),
  .DDR_odt(DDR_0_odt),
  .DDR_ras_n(DDR_0_ras_n),
  .DDR_reset_n(DDR_0_reset_n),
  .DDR_we_n(DDR_0_we_n),
  .FIXED_IO_ddr_vrn(FIXED_IO_0_ddr_vrn),
  .FIXED_IO_ddr_vrp(FIXED_IO_0_ddr_vrp),
  .FIXED_IO_mio(FIXED_IO_0_mio),
  .FIXED_IO_ps_clk(FIXED_IO_0_ps_clk),
  .FIXED_IO_ps_porb(FIXED_IO_0_ps_porb),
  .FIXED_IO_ps_srstb(FIXED_IO_0_ps_srstb),
  .shared_clk(clk_shared),
  .main_reset(ad_reset),
  .raw_frame_valid(raw_frame_valid),
  .raw_bank_id(raw_bank_id),
  .raw_frame_id(raw_frame_id),
  .raw_owner_token(raw_owner_token),
  .raw_status(raw_status),
  .raw_bank_states(raw_bank_states),
  .raw_ack_valid(raw_ack_valid),
  .raw_ack_bank_id(raw_ack_bank_id),
  .raw_ack_token(raw_ack_token),
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
  .raw_token_exhausted_sticky(raw_token_exhausted_sticky),
  .raw_read_en(raw_read_en),
  .raw_read_bank_id(raw_read_bank_id),
  .raw_read_index(raw_read_index),
  .raw_read_valid(raw_read_valid),
  .raw_read_data(raw_read_data));
endmodule

