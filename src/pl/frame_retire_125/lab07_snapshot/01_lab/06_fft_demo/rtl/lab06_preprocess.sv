`timescale 1ns/1ps
// The ROM is copied losslessly from frozen hann_q17.txt by the stage1 runner.
// Six registered stages. A shared clock enable holds the entire pipeline and
// its owner token when the output stalls; invalid data bits need no reset.
module lab06_preprocess #(parameter ROM_FILE="hann_q17.hex")(
 input logic clk,reset,flush,
 input logic input_valid, output logic input_ready,
 input logic [10:0] index,
 input logic signed [15:0] sample,
 input logic signed [26:0] frame_sum,
 input logic [45:0] input_token,
 output logic output_valid, input logic output_ready,
 output logic [45:0] output_token,
 output logic signed [24:0] windowed,
 output logic numeric_error
);
 logic [17:0] rom [0:2047];
 logic signed [27:0] centered;
 logic [17:0] coefficient;
 (* use_dsp="yes" *) logic signed [46:0] product,product_p;
 logic [46:0] magnitude;
 logic [26:0] rounded;
 logic negative_magnitude,negative_rounded;
 logic [5:0] valid;
 logic [45:0] token[0:5];
 logic advance;
 integer i;
 initial $readmemh(ROM_FILE,rom);
 assign advance=!valid[5] || output_ready;
 assign input_ready=advance && !reset && !flush;
 assign output_valid=valid[5] && !reset && !flush;
 assign output_token=token[5];
 always_ff @(posedge clk) begin
  if(reset || flush) valid<=0;
  else if(advance) begin
   valid<={valid[4:0],input_valid};
   token[0]<=input_token;
   for(i=1;i<6;i=i+1) token[i]<=token[i-1];
  end
  if(advance) begin
   // A/B input registers, followed by multiplier and product output registers.
   centered<=($signed({{12{sample[15]}},sample})<<<11)-$signed({frame_sum[26],frame_sum});
   coefficient<=rom[index];
   product<=centered*$signed({1'b0,coefficient});
   product_p<=product;
   magnitude<=product_p[46] ? -product_p : product_p;
   negative_magnitude<=product_p[46];
   rounded<=magnitude[46:20]+((magnitude[19:0]>20'h80000)||((magnitude[19:0]==20'h80000)&&magnitude[20]));
   negative_rounded<=negative_magnitude;
   numeric_error<=negative_rounded ? rounded>27'd16777216 : rounded>27'd16777215;
   windowed<=negative_rounded ? -$signed(rounded[24:0]) : $signed(rounded[24:0]);
  end
 end
endmodule
