`timescale 1ns/1ps
// Exact unsigned restoring divider and radix-4 integer square root.
// No truncation before the frozen floor operation. start only while !busy.
module lab06_udiv #(parameter W=129)(
 input logic clk, reset, start,
 input logic [W-1:0] numerator, denominator,
 output logic busy, done, error,
 output logic [W-1:0] quotient, remainder
);
 logic [W-1:0] dividend, divisor, q;
 logic [W:0] rem_work, trial, difference;
 logic subtract_phase;
 integer count;
 always_comb trial = {rem_work[W-1:0],dividend[W-1]};
 always_ff @(posedge clk) begin
  done<=0;
  // Working data is initialized on accepted start and guarded by busy.
  // Reset external outputs/validity; no runtime reset tree for dead work bits.
  if(reset) begin busy<=0; done<=0; error<=0; quotient<=0; remainder<=0; end
  else if(start && !busy) begin
   error<=denominator==0;
   if(denominator==0) begin done<=1; quotient<=0; remainder<=0; end
   else begin busy<=1; dividend<=numerator; divisor<=denominator; rem_work<=0; q<=0; count<=W;subtract_phase<=1; end
  end else if(busy) begin
   if(subtract_phase) begin
    // Extended subtract produces both exact difference and borrow. Separate
    // carry propagation from quotient/remainder selection and feedback.
    difference<=trial-{1'b0,divisor};subtract_phase<=0;
   end else begin
   subtract_phase<=1;
   dividend<=dividend<<1;
   if(!difference[W]) begin rem_work<=difference; q<={q[W-2:0],1'b1}; end
   else begin rem_work<=trial; q<={q[W-2:0],1'b0}; end
   count<=count-1;
   if(count==1) begin
    busy<=0; done<=1;
    quotient<={q[W-2:0],!difference[W]};
    remainder<=!difference[W] ? difference : trial;
   end
   end
  end
 end
endmodule

module lab06_isqrt #(parameter W=130)(
 input logic clk, reset, start, input logic [W-1:0] radicand,
 output logic busy, done, output logic [W/2-1:0] root
);
 localparam R=W/2;
 logic [W-1:0] bits_left;
 logic [R+1:0] rem_work, trial, sub;
 logic [R-1:0] r;
 integer count;
 always_comb begin
  trial=(rem_work<<2) | bits_left[W-1:W-2];
  sub=({2'b0,r}<<2) | 1;
 end
 always_ff @(posedge clk) begin
  done<=0;
  if(reset) begin busy<=0; done<=0; root<=0; end
  else if(start && !busy) begin busy<=1; bits_left<=radicand; r<=0; rem_work<=0; count<=R; end
  else if(busy) begin
   bits_left<=bits_left<<2; count<=count-1;
   if(trial>=sub) begin rem_work<=trial-sub; r<={r[R-2:0],1'b1}; end
   else begin rem_work<=trial; r<={r[R-2:0],1'b0}; end
   if(count==1) begin busy<=0; done<=1; root<={r[R-2:0],trial>=sub}; end
  end
 end
endmodule
