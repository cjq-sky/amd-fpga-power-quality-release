`timescale 1ns/1ps
// Local Lab06 entry; no Main, AXI, PS, acquisition or other Lab changes.
// Channel 1 occupies the low slice of each packed output.
module lab07_spectral_publication_top #(parameter ROM_FILE="hann_q17.hex")(
 input logic clk,reset,abort,
 input logic sample_valid,input logic [31:0] source_frame_id,
 input logic [10:0] sample_index,
 input logic signed [15:0] ch1,ch2,
 input logic [1:0] identity_ch1,identity_ch2,
 input logic [63:0] threshold_ch1_q24,threshold_ch2_q24,
 input logic [1:0] extreme,input logic source_error,
 output logic frame_error,protocol_error,bank_overrun,
 output logic publication_valid,input logic publication_ready,
 output logic [31:0] result_frame_id,
 output logic [31:0] status,
 output logic [1:0] result_valid,accuracy_qualified,
 output logic [31:0] accuracy_profile_id,
 output logic [53:0] fundamental_bins_q16,
 output logic [127:0] p1_selected_q24,
 output logic [319:0] harmonics_q16,
 output logic [63:0] thd_odd_3_5_7_9_q16,
 output logic [109:0] harmonic_centers,
 output logic [319:0] raw_harmonics_q16,
 output logic [63:0] raw_thd_q16,
 output logic [31:0] spectral_numeric_status,
 output logic [3:0] formal_identity
);
 typedef enum logic [2:0] {WAIT_BANK,START_CHANNEL,FEED,WAIT_FEATURE,STORE_CHANNEL,COMMIT,PUBLISH} state_t;
 state_t state;
 logic sealed_valid,sealed_bank,take,release_valid,active_bank,channel;
 logic [10:0] index;
 logic [1:0] occupied,clip;
 logic signed [15:0] r1,r2;
 logic signed [26:0] sum1,sum2;
 logic [31:0] fid;
 logic [131:0] controls;
 logic signed [24:0] windowed;
 logic pre_error;
 logic pre_input_valid,pre_input_ready,pre_valid,pre_ready,pre_flush;
 logic [45:0] pre_token;
 logic pipe_valid,pipe_ready,pipe_error;
 logic [45:0] pipe_token;
 logic signed [24:0] pipe_windowed;
 typedef enum logic [1:0] {READ_REQUEST,READ_RESPONSE,WAIT_TOKEN} feed_phase_t;
 feed_phase_t feed_phase;
 logic fft_idle,fft_ready,fft_svalid,fft_done,fft_error;
 logic signed [36:0] fft_re,fft_im;
 logic [10:0] fft_bin;
 logic [32:0] owner,fft_owner;
 logic feature_done;
 logic [15:0] feature_status;
 logic [26:0] feature_bin;
 logic [63:0] feature_power;
 logic [159:0] feature_h;
 logic [31:0] feature_thd;
 logic [54:0] feature_centers;
 logic [159:0] feature_raw_h;
 logic [31:0] feature_raw_thd;
 // Revision 1 numeric metadata: derived only from completed public outputs.
 logic [15:0] numeric_status_next;
 logic [47:0] encoded_frequency;
 logic frequency_guard_fail_q;
 // Interface-only cache. feature_bin is finalized long before STORE_CHANNEL;
 // arithmetic core and all FSM/handshake/publication latency remain unchanged.
 always_ff @(posedge clk) begin
  if(reset) begin encoded_frequency<=0;frequency_guard_fail_q<=1;end
  else begin
   encoded_frequency <= {21'b0,feature_bin} * 48'd10000000;
   frequency_guard_fail_q <= !(encoded_frequency >= 48'd39990*48'd2048*48'd65536 &&
                              encoded_frequency <= 48'd70010*48'd2048*48'd65536);
  end
 end
 always_comb begin
  numeric_status_next = 16'b0;
  numeric_status_next[1] = feature_status[10];
  numeric_status_next[2] = feature_status[2];
  numeric_status_next[3] = frequency_guard_fail_q;
  numeric_status_next[4] = feature_status[6];
  numeric_status_next[5] = feature_status[7];
  numeric_status_next[6] = feature_status[8];
  numeric_status_next[7] = feature_status[9];
  numeric_status_next[0] = (numeric_status_next & 16'h00ee) == 0;
 end
 always_ff @(posedge clk) begin
  if(reset) begin spectral_numeric_status<=0;formal_identity<=0;end
  else if(state==STORE_CHANNEL) begin
   spectral_numeric_status[16*channel+:16] <= numeric_status_next;
   formal_identity[2*channel+:2] <= channel ? controls[3:2] : controls[1:0];
  end
 end
 // Same STORE_CHANNEL capture as the existing packed production tuple.
 always_ff @(posedge clk) begin
  if(reset) begin raw_harmonics_q16<=0;raw_thd_q16<=0;end
  else if(state==STORE_CHANNEL) begin
   raw_harmonics_q16[160*channel+:160]<=feature_raw_h;
   raw_thd_q16[32*channel+:32]<=feature_raw_thd;
  end
 end
 assign take=state==WAIT_BANK && sealed_valid && fft_idle;
 assign release_valid=state==PUBLISH && publication_valid && publication_ready;
 assign owner={fid,channel};
 assign result_valid={status[16],status[0]};
 assign accuracy_qualified=2'b00;
 assign accuracy_profile_id=32'b0;
 lab06_frame_buffer buffer(
  .clk(clk),.reset(reset),.abort(abort),.sample_valid(sample_valid),.frame_id(source_frame_id),
  .sample_index(sample_index),.ch1(ch1),.ch2(ch2),.control({threshold_ch2_q24,threshold_ch1_q24,identity_ch2,identity_ch1}),
  .extreme(extreme),.source_error(source_error),.frame_error(frame_error),.protocol_error(protocol_error),.overrun(bank_overrun),
  .sealed_valid(sealed_valid),.sealed_bank(sealed_bank),.take(take),.release_valid(release_valid),.release_bank(active_bank),
  .read_bank(active_bank),.read_index(index),.read_ch1(r1),.read_ch2(r2),.read_frame_id(fid),.read_control(controls),
  .read_sum1(sum1),.read_sum2(sum2),.read_clip(clip),.occupied(occupied));
 // A single outstanding sample keeps the registered memory response and
 // pipeline token atomic. At 125 MHz this still exceeds the 10 kSPS source.
 assign pre_input_valid=state==FEED && feed_phase==READ_RESPONSE;
 assign pre_ready=state==FEED && fft_ready;
 // Local one-entry output holding register isolates the six-stage shared
 // advance from FFT ready/owner comparison. One outstanding sample remains.
 assign pipe_ready=!pre_valid;
 assign pre_flush=state==START_CHANNEL || (fft_done && fft_error);
 lab06_preprocess #(.ROM_FILE(ROM_FILE)) pre(
  .clk(clk),.reset(reset),.flush(pre_flush),
  .input_valid(pre_input_valid),.input_ready(pre_input_ready),
  .index(index),.sample(channel?r2:r1),.frame_sum(channel?sum2:sum1),
  .input_token({fid,active_bank,channel,index,index==2047}),
  .output_valid(pipe_valid),.output_ready(pipe_ready),.output_token(pipe_token),
  .windowed(pipe_windowed),.numeric_error(pipe_error));
 always_ff @(posedge clk) begin
  if(reset || pre_flush) pre_valid<=0;
  else begin
   if(pre_valid && pre_ready) pre_valid<=0;
   if(pipe_valid && pipe_ready) begin
    pre_valid<=1;pre_token<=pipe_token;windowed<=pipe_windowed;pre_error<=pipe_error;
   end
  end
 end
 lab06_fft_transaction fft(
  .clk(clk),.reset(reset),.start(state==START_CHANNEL && fft_idle),.owner(owner),.idle(fft_idle),
  .sample(windowed),.sample_valid(state==FEED && pre_valid),
  .sample_owner({pre_token[45:14],pre_token[12]}),.sample_ready(fft_ready),
  .re(fft_re),.im(fft_im),.bin(fft_bin),.spectrum_valid(fft_svalid),.done(fft_done),.error(fft_error),.result_owner(fft_owner));
 lab06_spectrum_features features(
  .clk(clk),.reset(reset),.start(state==START_CHANNEL && fft_idle),
  .identity(channel?controls[3:2]:controls[1:0]),
  .threshold_q24(channel?controls[131:68]:controls[67:4]),.clip_suspected(clip[channel]),
  .numeric_fault(state==FEED && pre_valid && fft_ready && pre_error),.fft_re(fft_re),.fft_im(fft_im),.fft_bin(fft_bin),
  .fft_valid(fft_svalid),.fft_done(fft_done),.fft_error(fft_error || (fft_done && fft_owner!=owner)),
  .done(feature_done),.status(feature_status),.fundamental_bin_q16(feature_bin),.p1_selected_q24(feature_power),
  .harmonics_q16(feature_h),.thd_q16(feature_thd),.centers_packed(feature_centers),
  .raw_harmonics_q16(feature_raw_h),.raw_thd_q16(feature_raw_thd));
 always_ff @(posedge clk) begin
  if(reset) begin
   state<=WAIT_BANK;active_bank<=0;channel<=0;index<=0;feed_phase<=READ_REQUEST;publication_valid<=0;result_frame_id<=0;
   status<=0;fundamental_bins_q16<=0;p1_selected_q24<=0;harmonics_q16<=0;thd_odd_3_5_7_9_q16<=0;harmonic_centers<=0;
  end else case(state)
   WAIT_BANK: if(take) begin active_bank<=sealed_bank;channel<=0;index<=0;state<=START_CHANNEL;end
   START_CHANNEL: if(fft_idle) begin state<=FEED;feed_phase<=READ_REQUEST;end
   FEED: begin
    if(fft_done && fft_error) state<=WAIT_FEATURE;
    else case(feed_phase)
     READ_REQUEST: feed_phase<=READ_RESPONSE;
     READ_RESPONSE: if(pre_input_ready) feed_phase<=WAIT_TOKEN;
     WAIT_TOKEN: if(pre_valid && fft_ready) begin
      if(pre_token[0]) state<=WAIT_FEATURE;
      else begin index<=index+1;feed_phase<=READ_REQUEST;end
     end
    endcase
   end
   WAIT_FEATURE: if(feature_done) state<=STORE_CHANNEL;
   STORE_CHANNEL: begin
    status[16*channel+:16]<=feature_status;
    fundamental_bins_q16[27*channel+:27]<=feature_bin;
    p1_selected_q24[64*channel+:64]<=feature_power;
    harmonics_q16[160*channel+:160]<=feature_h;
    thd_odd_3_5_7_9_q16[32*channel+:32]<=feature_thd;
    harmonic_centers[55*channel+:55]<=feature_centers;
    if(!channel) begin channel<=1;index<=0;state<=START_CHANNEL;end
    else state<=COMMIT;
   end
   COMMIT: begin result_frame_id<=fid;publication_valid<=1;state<=PUBLISH;end
   PUBLISH: if(publication_ready) begin publication_valid<=0;state<=WAIT_BANK;end
   default: state<=WAIT_BANK;
  endcase
 end
endmodule
