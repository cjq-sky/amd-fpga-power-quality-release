`timescale 1ns/1ps
// Transaction-level extension of feature/control AXI; no second owner FSM.
module lab07_raw_control(
 input wire clk,aresetn,main_reset,
 input wire owner_valid,owner_bank,
 input wire [31:0] owner_fid,owner_token,
 input wire [7:0] owner_status,bank_states,
 input wire [31:0] read_addr,
 output reg [31:0] read_data,
 input wire write_valid,
 input wire [31:0] write_addr,write_data,
 input wire [3:0] write_strb,
 output reg [1:0] write_resp,
 input wire read_busy,read_start,
 output reg ack_reservation,
 output wire raw_ack_valid,
 output reg raw_ack_bank_id,
 output reg [31:0] raw_ack_token
);
 reg bank_written,token_written;
 reg bank_staging;
 reg [31:0] token_staging;
 reg [7:0] result_code;
 reg [31:0] completed_token;
 wire args_valid=bank_written && token_written;
 // High between Ecmd and Ecmd+1, gated on reset. Manager samples at Ecmd+1.
 assign raw_ack_valid=aresetn && ack_reservation && !main_reset;
 always @* begin
  read_data=0;
  case(read_addr)
   32'h200:read_data={31'd0,owner_valid};
   32'h204:read_data=owner_valid?{31'd0,owner_bank}:0;
   32'h208:read_data=owner_valid?owner_fid:0;
   32'h20c:read_data=owner_valid?owner_token:0;
   32'h210:read_data=owner_valid?{24'd0,owner_status}:0;
   32'h214:read_data={24'd0,bank_states};
   32'h218:read_data={30'd0,bank_states[5:4]==2'd2,bank_states[1:0]==2'd2};
   32'h21c:read_data=32'd2048;
   32'h220:read_data=32'd3;
   32'h224:read_data=32'd8192;
   32'h228:read_data=0;
   32'h22c:read_data=32'd8192;
   32'h230:read_data=32'h00010001;
   32'h240:read_data={31'd0,bank_staging};
   32'h244:read_data=token_staging;
   32'h248:read_data=0;
   32'h24c:read_data={ack_reservation,23'd0,result_code};
   32'h250:read_data=completed_token;
  endcase
 end
 always @* begin
  write_resp=2'b10;
  if(!ack_reservation && !main_reset && write_strb==4'hf) begin
   case(write_addr)
    32'h240:if(write_data<=1) write_resp=0;
    32'h244:if(write_data!=0) write_resp=0;
    32'h248:if(write_data==0 || (write_data==1 && args_valid && !read_busy && !read_start)) write_resp=0;
   endcase
  end
 end
 always @(posedge clk) begin
  if(!aresetn) begin
   bank_written<=0;token_written<=0;bank_staging<=0;token_staging<=0;
   ack_reservation<=0;raw_ack_bank_id<=0;raw_ack_token<=0;result_code<=0;completed_token<=0;
  end else if(main_reset) begin
   bank_written<=0;token_written<=0;bank_staging<=0;token_staging<=0;
   if(ack_reservation || (write_valid && write_addr==32'h248 && write_data!=0)) result_code<=8'd4;
   ack_reservation<=0;completed_token<=0;
  end else if(ack_reservation) begin
   ack_reservation<=0;completed_token<=raw_ack_token;
   if(!owner_valid) result_code<=8'd3;
   else if(owner_bank!=raw_ack_bank_id || owner_token!=raw_ack_token) result_code<=8'd2;
   else result_code<=8'd1;
   // Writes during reservation are SLVERR; held command is never mutated.
  end else if(write_valid) begin
   case(write_addr)
    32'h240:begin
     bank_written<=write_strb==4'hf && write_data<=1;
     if(write_strb==4'hf && write_data<=1) bank_staging<=write_data[0];
    end
    32'h244:begin
     token_written<=write_strb==4'hf && write_data!=0;
     if(write_strb==4'hf && write_data!=0) token_staging<=write_data;
    end
    32'h248:begin
     if(!(write_strb==4'hf && write_data==0)) begin
      bank_written<=0;token_written<=0;
      completed_token<=token_written?token_staging:0;
      if(write_strb!=4'hf || write_data!=1 || !args_valid) result_code<=8'd5;
      else if(read_busy || read_start) result_code<=8'd6;
      else begin
       ack_reservation<=1;raw_ack_bank_id<=bank_staging;raw_ack_token<=token_staging;
       result_code<=0;
      end
     end
    end
   endcase
  end
 end
endmodule
