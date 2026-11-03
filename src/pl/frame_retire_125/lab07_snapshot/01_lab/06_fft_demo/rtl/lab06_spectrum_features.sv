`timescale 1ns/1ps
// All arithmetic follows the frozen integer kernel and V1 policy overlay.
// Storage is overwritten by a complete FFT before it is ever read.
module lab06_spectrum_features(
 input logic clk,reset,start,
 input logic [1:0] identity,
 input logic [63:0] threshold_q24,
 input logic clip_suspected,numeric_fault,
 input logic signed [36:0] fft_re,fft_im,
 input logic [10:0] fft_bin,
 input logic fft_valid,fft_done,fft_error,
 output logic done,
 output logic [15:0] status,
 output logic [26:0] fundamental_bin_q16,
 output logic [63:0] p1_selected_q24,
 output logic [159:0] harmonics_q16,
 output logic [31:0] thd_q16,
 output logic [54:0] centers_packed,
 output logic [159:0] raw_harmonics_q16,
 output logic [31:0] raw_thd_q16
);
 localparam [128:0] D=129'd27021598589386752;
 // Keep original state codes for existing lifecycle/fault phase probes.
 typedef enum logic [5:0] {IDLE,CAPTURE,ROOT_START,ROOT_WAIT,DELTA_START,DELTA_WAIT,
  DELTA_FINISH,GEOMETRY,BAND,POWER_START,POWER_WAIT,H_DIV_START,H_DIV_WAIT,
  H_ROOT_START,H_ROOT_WAIT,THD_DIV_START,THD_DIV_WAIT,THD_ROOT_START,THD_ROOT_WAIT,POLICY,COMPLETE,
  DRAIN,PEAK_READ,PEAK_SAMPLE,PEAK_UPDATE,ROOT_READ,BAND_READ,
  DELTA_ROUND_TEST,DELTA_ROUND_ADD,DELTA_CLAMP,GEOMETRY_CALC} state_t;
 state_t state;
 (* ram_style="block" *) logic [74:0] g[0:1023];
 logic signed [36:0] sample_re,sample_im;
 (* use_dsp="yes" *) logic signed [73:0] re2,im2,re2_p,im2_p;
 logic [74:0] power;
 logic [3:0] power_valid;
 logic [10:0] power_bin[0:3];
 logic [9:0] g_address;
 logic [74:0] g_read,peak_candidate;
 logic [3:0] peak_scan;
 logic round_up;
 logic [26:0] clamped_delta;
 logic [31:0] geometry_center[0:4];
 logic [74:0] peak;
 logic [10:0] peak_bin,centers[0:4];
 logic [77:0] bands[0:4];
 logic [79:0] odd_power;
 logic [37:0] neighbors[0:2];
 logic [39:0] delta_den;
 logic delta_den_zero;
 logic signed [39:0] delta_num;
 logic [128:0] delta_magnitude,rounded_delta;
 logic delta_negative,positive,geometry_ok,guard_ok,strict_ok,overflow;
 logic [1:0] locked_identity;
 logic [63:0] locked_threshold;
 logic locked_clip,locked_numeric;
 logic [128:0] numerator,denominator,quotient,remainder;
 logic div_start,div_busy,div_done,div_error;
 logic [129:0] radicand;
 logic [64:0] root;
 logic sqrt_start,sqrt_busy,sqrt_done;
 logic [31:0] h[0:4],thd;
 // Read-only observation mirror, before the frozen production policy mux.
 // Existing arithmetic, state, latency and production outputs are untouched.
 always_ff @(posedge clk) begin
  if(reset || (state==IDLE && start)) begin
   raw_harmonics_q16<=0;raw_thd_q16<=0;
  end else if(state==POLICY) begin
   for(integer raw_i=0;raw_i<5;raw_i=raw_i+1)
    raw_harmonics_q16[32*raw_i+:32]<=h[raw_i];
   raw_thd_q16<=thd;
  end
 end
 logic [15:0] policy_status;
 (* use_dsp="yes" *) logic [47:0] fq_mul,fq;
 integer item,neighbor,offset,i,j;
 function automatic integer order(input integer idx);
  order=2*idx+1;
 endfunction
 lab06_udiv div_unit(clk,reset,div_start,numerator,denominator,div_busy,div_done,div_error,quotient,remainder);
 lab06_isqrt sqrt_unit(clk,reset,sqrt_start,radicand,sqrt_busy,sqrt_done,root);
 // FFT_valid is already an accepted AXIS output token. No ready is fed back:
 // this pipeline accepts one complete (sample,bin) tuple every clock.
 // Owner/status are immutable from start to COMPLETE; reset/start kill all
 // token validity. No data reset is needed for the overwritten spectrum.
 always_ff @(posedge clk) begin
  if(reset || (state==IDLE && start) || (fft_done && fft_error)) power_valid<=0;
  else power_valid<={power_valid[2:0],state==CAPTURE && fft_valid};
  sample_re<=fft_re;sample_im<=fft_im;power_bin[0]<=fft_bin;
  re2<=sample_re*sample_re;im2<=sample_im*sample_im;
  re2_p<=re2;im2_p<=im2;
  power<={1'b0,re2_p}+{1'b0,im2_p};
  // Fundamental is finalized before geometry/band/divide/root scheduling.
  // These two cache registers settle long before any guard/policy consumer.
  // Preserve the original 48-bit product and every exact threshold compare.
  fq_mul<={21'b0,fundamental_bin_q16}*48'd10000000;
  fq<=fq_mul;
  for(integer k=1;k<4;k=k+1) power_bin[k]<=power_bin[k-1];
 end
 // One synchronous read port shared by peak, neighbor and band scheduling.
 // DRAIN completes all writes before the first read (no read/write collision).
 always_comb begin
  g_address=0;
  case(state)
   PEAK_READ:g_address=peak_scan;
   ROOT_READ:g_address=peak_bin+neighbor-1;
   BAND_READ:g_address=centers[item]-2+offset;
   default:g_address=0;
  endcase
 end
 always_ff @(posedge clk) begin
  if(!reset && (state==CAPTURE || state==DRAIN) && power_valid[3] && power_bin[3]<1024)
   g[power_bin[3]]<=power;
  if(state==PEAK_READ || state==ROOT_READ || state==BAND_READ) g_read<=g[g_address];
 end
 always_comb begin
  delta_den={2'b0,neighbors[0]}+({2'b0,neighbors[1]}<<1)+{2'b0,neighbors[2]};
  // Nonnegative 38-bit terms sum to at most 2^40-4: zero iff all are zero.
  delta_den_zero=~(|{neighbors[0],neighbors[1],neighbors[2]});
  delta_num=2*($signed({2'b0,neighbors[2]})-$signed({2'b0,neighbors[0]}));
  delta_magnitude=delta_num[39] ? -$signed(delta_num) : delta_num;
  guard_ok=positive && fq>=48'd39990*48'd2048*48'd65536 && fq<=48'd70010*48'd2048*48'd65536;
  strict_ok=fq>=48'd40000*48'd2048*48'd65536 && fq<=48'd70000*48'd2048*48'd65536;
  odd_power={2'b0,bands[1]}+{2'b0,bands[2]}+{2'b0,bands[3]}+{2'b0,bands[4]};
  policy_status=0;
  if(!positive || locked_identity==3) policy_status[3]=1;
  if(p1_selected_q24<=locked_threshold) policy_status[2]=1;
  if(locked_identity==0 || locked_identity==2) policy_status[4]=1;
  if(positive && !guard_ok) policy_status[5]=1;
  if(guard_ok && !strict_ok) policy_status[6]=1;
  if(!geometry_ok) policy_status[7]=1;
  policy_status[8]=locked_clip;
  policy_status[9]=locked_numeric||overflow;
  if((policy_status & 16'h1fbc)==0 && locked_identity==1 && positive && guard_ok) policy_status[0]=1;
 end
 always_ff @(posedge clk) begin
  done<=0;div_start<=0;sqrt_start<=0;
  if(reset) begin
   state<=IDLE;status<=0;fundamental_bin_q16<=0;p1_selected_q24<=0;harmonics_q16<=0;thd_q16<=0;centers_packed<=0;
   div_start<=0;sqrt_start<=0;
   // All work registers are written by start or the preceding algorithm
   // state before use. Reset gates state/token validity and visible outputs;
   // stale arithmetic/storage data cannot be consumed by a new owner.
  end else begin
   case(state)
    IDLE: if(start) begin
     state<=CAPTURE;locked_identity<=identity;locked_threshold<=threshold_q24;locked_clip<=clip_suspected;
     locked_numeric<=numeric_fault;overflow<=0;peak<=0;peak_bin<=8;positive<=0;geometry_ok<=0;
     fundamental_bin_q16<=0;p1_selected_q24<=0;harmonics_q16<=0;thd_q16<=0;status<=0;thd<=0;
     for(i=0;i<5;i=i+1) begin bands[i]<=0;h[i]<=0;end
    end
    CAPTURE: begin
     locked_numeric<=locked_numeric||numeric_fault;
     if(fft_done) begin
      if(fft_error) begin
       status<=16'h0400 | (locked_clip?16'h0100:0) | (locked_numeric?16'h0200:0);
       centers_packed<=0;state<=COMPLETE;
      end else state<=DRAIN;
     end
    end
    DRAIN: if(power_valid==0) begin peak_scan<=8;state<=PEAK_READ;end
    PEAK_READ: state<=PEAK_SAMPLE;
    PEAK_SAMPLE: begin peak_candidate<=g_read;state<=PEAK_UPDATE;end
    PEAK_UPDATE: begin
     // Ascending scan and strict '>' preserve the first-bin tie rule.
     if(peak_candidate>peak) begin peak<=peak_candidate;peak_bin<=peak_scan;end
     if(peak_scan==15) begin neighbor<=0;state<=ROOT_READ;end
     else begin peak_scan<=peak_scan+1;state<=PEAK_READ;end
    end
    ROOT_READ: state<=ROOT_START;
    ROOT_START: begin radicand<={55'b0,g_read};sqrt_start<=1;state<=ROOT_WAIT;end
    ROOT_WAIT: if(sqrt_done) begin
     neighbors[neighbor]<=root[37:0];
     if(neighbor==2) state<=DELTA_START;
     else begin neighbor<=neighbor+1;state<=ROOT_READ;end
    end
    DELTA_START: begin
     positive<=!delta_den_zero;delta_negative<=delta_num[39];
     if(delta_den_zero) begin fundamental_bin_q16<={peak_bin,16'b0};state<=GEOMETRY_CALC;end
     else begin numerator<=delta_magnitude<<16;denominator<=delta_den;div_start<=1;state<=DELTA_WAIT;end
    end
    DELTA_WAIT: if(div_done) state<=DELTA_ROUND_TEST;
    DELTA_ROUND_TEST: begin
     round_up<=(remainder*2>denominator)||((remainder*2==denominator)&&quotient[0]);
     state<=DELTA_ROUND_ADD;
    end
    DELTA_ROUND_ADD: begin rounded_delta<=quotient+round_up;state<=DELTA_CLAMP;end
    DELTA_CLAMP: begin clamped_delta<=rounded_delta>32768 ? 27'd32768 : rounded_delta[26:0];state<=DELTA_FINISH;end
    DELTA_FINISH: begin
     if(delta_negative) fundamental_bin_q16<=({peak_bin,16'b0})-clamped_delta;
     else fundamental_bin_q16<=({peak_bin,16'b0})+clamped_delta;
     state<=GEOMETRY_CALC;
    end
    GEOMETRY_CALC: begin
     for(i=0;i<5;i=i+1) geometry_center[i]<=((fundamental_bin_q16*order(i))+32768)>>16;
     state<=GEOMETRY;
    end
    GEOMETRY: begin
     geometry_ok<=1;
     for(i=0;i<5;i=i+1) begin
      centers[i]<=geometry_center[i];
      centers_packed[11*i+:11]<=geometry_center[i];
      if(geometry_center[i]<3 || geometry_center[i]>1021) geometry_ok<=0;
      for(j=0;j<i;j=j+1) if(geometry_center[i]-geometry_center[j]<=4) geometry_ok<=0;
     end
     item<=0;offset<=0;state<=BAND_READ;
    end
    BAND_READ: state<=BAND;
    BAND: begin
     if(geometry_ok) bands[item]<=bands[item]+g_read;
     if(offset==4) begin offset<=0;if(item==4) state<=POWER_START;else begin item<=item+1;state<=BAND_READ;end end
     else begin offset<=offset+1;state<=BAND_READ;end
    end
    POWER_START: begin numerator<={51'b0,bands[0]}<<43;denominator<=D;div_start<=1;state<=POWER_WAIT;end
    POWER_WAIT: if(div_done) begin p1_selected_q24<=quotient[63:0];if(|quotient[128:64] || div_error) overflow<=1;item<=0;state<=H_DIV_START;end
    H_DIV_START: begin numerator<={51'b0,bands[item]}<<51;denominator<=D;div_start<=1;state<=H_DIV_WAIT;end
    H_DIV_WAIT: if(div_done) begin radicand<={1'b0,quotient};if(div_error) overflow<=1;state<=H_ROOT_START;end
    H_ROOT_START: begin sqrt_start<=1;state<=H_ROOT_WAIT;end
    H_ROOT_WAIT: if(sqrt_done) begin
     h[item]<=root[31:0];if(|root[64:32]) overflow<=1;
     if(item==4) begin
      if(guard_ok && geometry_ok && bands[0]!=0) state<=THD_DIV_START;
      else state<=POLICY;
     end else begin item<=item+1;state<=H_DIV_START;end
    end
    THD_DIV_START: begin numerator<={49'b0,odd_power}<<32;denominator<=bands[0];div_start<=1;state<=THD_DIV_WAIT;end
    THD_DIV_WAIT: if(div_done) begin radicand<={1'b0,quotient};if(div_error) overflow<=1;state<=THD_ROOT_START;end
    THD_ROOT_START: begin sqrt_start<=1;state<=THD_ROOT_WAIT;end
    THD_ROOT_WAIT: if(sqrt_done) begin thd<=root[31:0];if(|root[64:32]) overflow<=1;state<=POLICY;end
    POLICY: begin
     status<=policy_status;
     for(i=0;i<5;i=i+1) harmonics_q16[32*i+:32]<=policy_status[0] ? h[i] : 0;
     thd_q16<=policy_status[0] ? thd : 0;state<=COMPLETE;
    end
    COMPLETE: begin done<=1;state<=IDLE;end
    default: state<=IDLE;
   endcase
  end
 end
endmodule
