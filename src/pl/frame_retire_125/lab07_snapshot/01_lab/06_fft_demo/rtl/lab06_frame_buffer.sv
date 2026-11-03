`timescale 1ns/1ps
// Input is an inseparable synchronous pair. No independent CH1/CH2 enables.
// control={threshold_ch2,threshold_ch1,identity_ch2,identity_ch1} is locked
// at index0 and checked on each accepted sample. identity encoding:
// 0 UNKNOWN, 1 ACCEPTED, 2 AMBIGUOUS, 3 NOT_FOUND.
module lab06_frame_buffer(
 input logic clk,reset,abort,
 input logic sample_valid, input logic [31:0] frame_id,
 input logic [10:0] sample_index,
 input logic signed [15:0] ch1,ch2,
 input logic [131:0] control,
 input logic [1:0] extreme,
 input logic source_error,
 output logic frame_error,protocol_error,overrun,
 output logic sealed_valid, output logic sealed_bank,
 input logic take, input logic release_valid,release_bank,
 input logic read_bank, input logic [10:0] read_index,
 output logic signed [15:0] read_ch1,read_ch2,
 output logic [31:0] read_frame_id,
 output logic [131:0] read_control,
 output logic signed [26:0] read_sum1,read_sum2,
 output logic [1:0] read_clip,
 output logic [1:0] occupied
);
 (* ram_style="block" *) logic signed [15:0] mem1[0:4095],mem2[0:4095];
 logic sample_write;
 logic [11:0] write_address;
 logic [31:0] ids[0:1];
 logic [131:0] controls[0:1];
 logic signed [26:0] sums1[0:1],sums2[0:1];
 logic [1:0] clips[0:1],sealed;
 logic active,fill_bank,oldest;
 logic [11:0] expected_index;
 logic free_bank,has_free;
 logic [1:0] sample_clip;
 assign sample_clip=extreme|{(ch2==-32768 || ch2==32767),(ch1==-32768 || ch1==32767)};
 assign has_free=!(&occupied);
 assign free_bank=occupied[0];
 assign sealed_valid=|sealed;
 assign sealed_bank=sealed==2'b11 ? oldest : sealed[1];
 // One synchronous read and one write port per channel. The data memories
 // have no reset; occupied/sealed prevent consumption of stale contents.
 // Keep writes outside the metadata reset tree for stable SDP BRAM inference.
 assign sample_write=!reset && !abort && sample_valid && !source_error &&
  ((active && frame_id==ids[fill_bank] && sample_index==expected_index && control==controls[fill_bank]) ||
   (!active && sample_index==0 && has_free));
 assign write_address={active ? fill_bank : free_bank,sample_index};
 always_ff @(posedge clk) begin
  if(sample_write) begin mem1[write_address]<=ch1;mem2[write_address]<=ch2;end
  read_ch1<=mem1[{read_bank,read_index}];
  read_ch2<=mem2[{read_bank,read_index}];
 end
 assign read_frame_id=ids[read_bank];
 assign read_control=controls[read_bank];
 assign read_sum1=sums1[read_bank]; assign read_sum2=sums2[read_bank];
 assign read_clip=clips[read_bank];
 integer i;
 always_ff @(posedge clk) begin
  frame_error<=0; protocol_error<=0; overrun<=0;
  if(reset) begin
   active<=0; occupied<=0; sealed<=0; expected_index<=0; fill_bank<=0; oldest<=0;
   for(i=0;i<2;i=i+1) begin ids[i]<=0;controls[i]<=0;sums1[i]<=0;sums2[i]<=0;clips[i]<=0;end
  end else begin
   if(release_valid) occupied[release_bank]<=0;
   if(take && sealed_valid) begin sealed[sealed_bank]<=0; oldest<=!sealed_bank; end
   if(abort) begin
    if(active) begin occupied[fill_bank]<=0; active<=0; frame_error<=1; end
   end else if(sample_valid) begin
    if(active) begin
     if(source_error || frame_id!=ids[fill_bank] || sample_index!=expected_index || control!=controls[fill_bank]) begin
      occupied[fill_bank]<=0; active<=0; frame_error<=1;protocol_error<=1;
     end else begin
      sums1[fill_bank]<=sums1[fill_bank]+$signed(ch1);
      sums2[fill_bank]<=sums2[fill_bank]+$signed(ch2);
      clips[fill_bank]<=clips[fill_bank]|sample_clip;
      expected_index<=expected_index+1;
      if(sample_index==2047) begin
       active<=0;sealed[fill_bank]<=1;
       if(sealed==0 || (take && sealed_valid)) oldest<=fill_bank;
      end
     end
    end else if(sample_index==0) begin
     if(source_error) begin frame_error<=1;protocol_error<=1; end
     else if(!has_free) overrun<=1;
     else begin
      active<=1;fill_bank<=free_bank;occupied[free_bank]<=1;expected_index<=1;
      ids[free_bank]<=frame_id;controls[free_bank]<=control;
      sums1[free_bank]<=$signed(ch1);sums2[free_bank]<=$signed(ch2);clips[free_bank]<=sample_clip;
     end
    end
   end
  end
 end
endmodule
