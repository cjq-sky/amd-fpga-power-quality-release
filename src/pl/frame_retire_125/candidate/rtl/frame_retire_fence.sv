`timescale 1ns/1ps
// Fixed aligned 32-bit MM2S geometry. Credits originate at the real command
// generation edge, before any DataMover buffering, never from frame pointers.
module frame_retire_fence #(
 parameter integer FRAME_BYTES=2764800, LINE_BYTES=3840,
 parameter integer DEADLINE_CYCLES=125000000, QDEPTH=64
)(
 input wire clk, resetn, enable, external_fault,
 input wire [127:0] generation,
 input wire [31:0] base0,base1,base2,base3,
 input wire req, consume,
 input wire [63:0] req_seq, consume_seq,
 input wire [1:0] req_slot,
 input wire frame_start, command_generate, last_command,
 input wire command_accept, status_accept,
 input wire [7:0] status_data,
 input wire [31:0] core_araddr,
 input wire [7:0] core_arlen,
 input wire [2:0] core_arsize,
 input wire [1:0] core_arburst,
 input wire [2:0] core_arprot,
 input wire [3:0] core_arcache,
 input wire core_arvalid, memory_arready,
 output wire memory_arvalid, core_arready,
 output wire [31:0] memory_araddr,
 output wire [7:0] memory_arlen,
 output wire [2:0] memory_arsize,memory_arprot,
 output wire [1:0] memory_arburst,
 output wire [3:0] memory_arcache,
 input wire response_valid,response_ready,response_last,
 input wire [1:0] response_code,
 output wire [31:0] next_base,
 output reg [1:0] active_slot,
 output reg started, busy, accepted, retire_valid,
 output reg [63:0] accepted_seq,retire_seq,
 output reg [1:0] retire_slot,
 output reg [31:0] error_status
);
 localparam integer LINE_BEATS=LINE_BYTES/4;
 // The production geometry has 128-byte-aligned commands and a 32-beat
 // DataMover burst limit. Every line is an exact multiple of that burst;
 // 4KiB splits are also exact. Reject any deviation rather than guessing its
 // responsibility. Small generic unit-test geometries retain variable bursts.
 localparam integer FIXED_BURSTS=(LINE_BYTES==3840 && FRAME_BYTES%128==0);
 reg [31:0] unissued[0:3];
 reg [31:0] outstanding[0:3];
 reg owned[0:3];
 reg [1:0] pending_slot,old_slot;
 reg [63:0] pending_seq,last_seq;
 reg switching,frame_complete;
 reg [31:0] elapsed;
 // R7-A: only the head owns mutable response progress. Tail records are
 // immutable from enqueue until promotion; no selected array entry is ever
 // decremented and written back through the queue-wide response/error cone.
 reg head_valid;
 reg [1:0] head_slot;
 reg [8:0] head_remaining;
 reg [1:0] tail_slot[0:QDEPTH-1];
 reg [8:0] tail_beats[0:QDEPTH-1];
 integer rdptr,wrptr,generated_commands,accepted_commands;
 // Admission caps this queue at QDEPTH. Include the full-depth value itself.
 reg [$clog2(QDEPTH+1)-1:0] burst_count;
 integer i;
 reg [31:0] cycle_errors;
 reg ar_hold;
 reg [31:0] ar_addr;
 reg [7:0] ar_len;
 reg [2:0] ar_size,ar_prot;
 reg [1:0] ar_burst;
 reg [3:0] ar_cache;
 reg [$clog2(QDEPTH+1)-1:0] externally_posted;
 reg [31:0] bases[0:3];
 reg [1:0] address_slot;
 reg address_found,address_overlap;
 reg [32:0] ar_end;
 // Dynamic-only ingress has no combinational READY fall-through. A raw
 // DataMover request accepted here remains covered by unissued line credits
 // until validation moves it to the guarded AR hold and burst ledger.
 reg ingress_valid;
 reg [31:0] ingress_addr;
 reg [7:0] ingress_len;
 reg [2:0] ingress_size,ingress_prot;
 reg [1:0] ingress_burst;
 reg [3:0] ingress_cache;
 // R6: decode ownership ranges at the same ingress handshake as the payload.
 // The armed register bank freezes base0..3 while enable is asserted. These
 // four hit bits therefore remain associated with this exact queued request;
 // credit, ownership, fault and queue-capacity checks still use admission time.
 reg [3:0] ingress_range_hit;
 reg [3:0] core_range_hit;
 reg [24:0] core_relative_block;
 reg [32:0] core_ar_end;
 wire admission_ready;
 wire [8:0] ar_beats=FIXED_BURSTS ? 9'd32:({1'b0,ingress_len}+9'd1);
 wire ar_take=ingress_valid && admission_ready;
 wire external_ar_take=memory_arvalid && memory_arready;
 wire r_take=response_valid && response_ready;
 wire head_pop=r_take && head_valid && head_remaining==1;
 // With one record, simultaneous pop/push replaces the head directly.
 // Total capacity remains QDEPTH, including the head (tail <= QDEPTH-1).
 wire tail_push=ar_take && head_valid && !(head_pop && burst_count==1);
 wire gen_take=enable && command_generate;
 wire switch_now=enable && frame_start && started && busy && !switching && !retire_valid && !error_status;
 wire [1:0] select_slot=switch_now ? pending_slot:active_slot;
 wire good_ar=address_found && !address_overlap && owned[address_slot] &&
              unissued[address_slot]>=ar_beats && burst_count<QDEPTH &&
              ingress_size==3'd2 && ingress_burst==2'd1 && ingress_addr[1:0]==0 &&
              (FIXED_BURSTS ? ingress_len==31:ingress_len<32) && !error_status;
 // In static mode all signals remain transparent. Dynamic mode never forwards
 // an address without a generated command's unspent beat credits.
 assign memory_arvalid=enable ? ar_hold:core_arvalid;
 assign admission_ready=enable && (!ar_hold || memory_arready) && good_ar;
 assign core_arready=enable ? (!ingress_valid && !error_status):memory_arready;
 assign memory_araddr=enable ? ar_addr:core_araddr;
 assign memory_arlen=enable ? ar_len:core_arlen;
 assign memory_arsize=enable ? ar_size:core_arsize;
 assign memory_arburst=enable ? ar_burst:core_arburst;
 assign memory_arprot=enable ? ar_prot:core_arprot;
 assign memory_arcache=enable ? ar_cache:core_arcache;
 assign next_base=bases[select_slot];
 always @(posedge clk) begin
  if(!resetn) begin
   ingress_valid<=0;ingress_addr<=0;ingress_len<=0;ingress_size<=0;
   ingress_burst<=0;ingress_prot<=0;ingress_cache<=0;
   ingress_range_hit<=0;
  end else if(!enable) ingress_valid<=0;
  else begin
   if(ingress_valid && admission_ready)ingress_valid<=0;
   if(core_arvalid && core_arready)begin
    ingress_valid<=1;ingress_addr<=core_araddr;ingress_len<=core_arlen;
    ingress_size<=core_arsize;ingress_burst<=core_arburst;
    ingress_prot<=core_arprot;ingress_cache<=core_arcache;
    ingress_range_hit<=core_range_hit;
   end
  end
 end
 // Keep the arithmetic off the late AR admission control. The old form
 // added a conditional burst and then subtracted R in a serial carry chain.
 wire [31:0] unissued_add[0:3],unissued_sub[0:3],unissued_both[0:3];
 wire [31:0] outstanding_add[0:3],outstanding_sub[0:3],outstanding_both[0:3];
 for(genvar g=0;g<4;g=g+1) begin: ledger_arithmetic
  (* KEEP="TRUE" *) wire [31:0] ua=unissued[g]+LINE_BEATS;
  (* KEEP="TRUE" *) wire [31:0] us=unissued[g]-ar_beats;
  (* KEEP="TRUE" *) wire [31:0] ub=unissued[g]+(LINE_BEATS-ar_beats);
  (* KEEP="TRUE" *) wire [31:0] oa=outstanding[g]+ar_beats;
  (* KEEP="TRUE" *) wire [31:0] os=outstanding[g]-1'b1;
  (* KEEP="TRUE" *) wire [31:0] ob=outstanding[g]+(ar_beats-1'b1);
  assign unissued_add[g]=ua;assign unissued_sub[g]=us;assign unissued_both[g]=ub;
  assign outstanding_add[g]=oa;assign outstanding_sub[g]=os;assign outstanding_both[g]=ob;
 end
 always @* begin
  bases[0]=base0;bases[1]=base1;bases[2]=base2;bases[3]=base3;
  core_range_hit=0;
  core_ar_end={1'b0,core_araddr}+((33'd1+{25'b0,core_arlen})<<2);
  core_relative_block=0;
  for(integer j=0;j<4;j=j+1) begin
   // Bases are arm-checked inside HP0. Subtraction in 128-byte units cannot
   // wrap into this small window for another HP0 address. No ARLEN->33-bit
   // end-address adder or per-slot end-address adder is on the production path.
   core_relative_block=core_araddr[31:7]-bases[j][31:7];
   if(FIXED_BURSTS ? (core_araddr[31:29]==0 && core_araddr[6:0]==0 && core_relative_block<FRAME_BYTES/128):
      (core_araddr>=bases[j] && core_ar_end<=({1'b0,bases[j]}+FRAME_BYTES)))
    core_range_hit[j]=1'b1;
  end
 end
 always @* begin
  address_found=0;address_overlap=0;address_slot=0;
  for(integer j=0;j<4;j=j+1) begin
   if(ingress_range_hit[j]) begin
    if(address_found) address_overlap=1;
    address_found=1;address_slot=j;
   end
  end
 end
 task fault(input [31:0] code);
  begin cycle_errors=cycle_errors|code;end
 endtask
 always @(posedge clk) begin
  if(!resetn) begin
   active_slot<=0;started<=0;busy<=0;accepted<=0;retire_valid<=0;
   accepted_seq<=0;retire_seq<=0;retire_slot<=0;error_status<=0;
   pending_slot<=0;old_slot<=0;pending_seq<=0;last_seq<=0;
   switching<=0;frame_complete<=0;elapsed<=0;
   rdptr<=0;wrptr<=0;burst_count<=0;generated_commands<=0;accepted_commands<=0;
   head_valid<=0;head_slot<=0;head_remaining<=0;
   ar_hold<=0;ar_addr<=0;ar_len<=0;ar_size<=0;ar_burst<=0;ar_prot<=0;ar_cache<=0;externally_posted<=0;
   for(i=0;i<4;i=i+1) begin unissued[i]<=0;outstanding[i]<=0;owned[i]<=i==0;end
  end else if(enable) begin
   cycle_errors=0;
   if(!ar_hold || memory_arready) begin
    ar_hold<=ar_take;
    if(ar_take) begin
     ar_addr<=ingress_addr;ar_len<=ingress_len;ar_size<=ingress_size;
     ar_burst<=ingress_burst;ar_prot<=ingress_prot;ar_cache<=ingress_cache;
    end
   end
   externally_posted<=externally_posted+(external_ar_take?1:0)-((r_take && response_last)?1:0);
   if(r_take && externally_posted==0 && !external_ar_take) fault(32'h8);
   // Byte responsibilities and AR FIFO advance together, including simultaneous
   // command generation, address handshake, and response handshake.
   for(i=0;i<4;i=i+1) begin
    case({(gen_take && active_slot==i),(ar_take && address_slot==i)})
     2'b10:unissued[i]<=unissued_add[i];
     2'b01:unissued[i]<=unissued_sub[i];
     2'b11:unissued[i]<=unissued_both[i];
     default:;
    endcase
    case({(ar_take && address_slot==i),(r_take && head_valid && head_slot==i)})
     2'b10:outstanding[i]<=outstanding_add[i];
     2'b01:outstanding[i]<=outstanding_sub[i];
     2'b11:outstanding[i]<=outstanding_both[i];
     default:;
    endcase
    if(gen_take && active_slot==i && unissued[i]>32'hffff0000) fault(32'h100);
   end
   if(tail_push) begin
    tail_slot[wrptr]<=address_slot;tail_beats[wrptr]<=ar_beats;
    wrptr<=(wrptr+1)%QDEPTH;
   end
   if(!head_valid) begin
    if(ar_take) begin
     head_valid<=1;head_slot<=address_slot;head_remaining<=ar_beats;
    end
   end else if(r_take) begin
    if(response_last != (head_remaining==1) || response_code!=0)
     fault(32'h4);
    if(head_remaining==1) begin
     if(burst_count>1) begin
      head_slot<=tail_slot[rdptr];head_remaining<=tail_beats[rdptr];
      rdptr<=(rdptr+1)%QDEPTH;
     end else if(ar_take) begin
      head_slot<=address_slot;head_remaining<=ar_beats;
     end else head_valid<=0;
    end else head_remaining<=head_remaining-1'b1;
   end
   burst_count<=burst_count+(ar_take?1:0)-(head_pop?1:0);
   if(r_take && burst_count==0) fault(32'h8);
   // Diagnostic command/status responsibility is NOT the retire fence. Credits
   // and the guarded DDR port remain authoritative even for an early status.
   generated_commands<=generated_commands+(gen_take?1:0)-(status_accept?1:0);
   accepted_commands<=accepted_commands+(command_accept?1:0)-(status_accept?1:0);
   if(status_accept && (accepted_commands==0 || generated_commands==0 ||
       !status_data[7] || status_data[6:4]!=0 || status_data[3:0]!=4'h3)) fault(32'h10);
   if(command_accept && accepted_commands>=generated_commands && !gen_take) fault(32'h10);
   if(frame_start) begin
    if(command_generate) fault(32'h20);
    if(started && !frame_complete) fault(32'h20);
    started<=1;frame_complete<=0;
    if(switch_now) begin
     old_slot<=active_slot;active_slot<=pending_slot;switching<=1;
    end
   end
   if(gen_take && last_command) frame_complete<=1;
   if(req && !error_status) begin
    if(busy || retire_valid || req_slot==active_slot || owned[req_slot] ||
       req_seq==0 || req_seq<=last_seq || generation==0) fault(32'h1);
    else begin
     busy<=1;accepted<=1;accepted_seq<=req_seq;pending_seq<=req_seq;
     pending_slot<=req_slot;last_seq<=req_seq;owned[req_slot]<=1;elapsed<=0;
    end
   end
   if(busy && !retire_valid) begin
    if(elapsed>=DEADLINE_CYCLES-1) fault(32'h40);
    else elapsed<=elapsed+1'b1;
   end
   // One cycle after the final response: old credits and accepted beats must
   // both be zero. The source epoch is closed and the guard forbids any late AR.
   if(switching && !error_status && !external_fault &&
      unissued[old_slot]==0 && outstanding[old_slot]==0 &&
      !(ingress_valid && address_found && address_slot==old_slot)) begin
    retire_valid<=1;retire_seq<=pending_seq;retire_slot<=old_slot;
    owned[old_slot]<=0;switching<=0;
   end
   if(consume) begin
    if(!retire_valid || consume_seq!=retire_seq) fault(32'h2);
    else begin retire_valid<=0;busy<=0;accepted<=0;end
   end
   if(ingress_valid && !good_ar && burst_count<QDEPTH) begin
    // Insufficient queue capacity is legal backpressure; every other invalid
    // request is a protocol/ownership error and is blocked before DDR.
    fault(32'h80);
   end
   if(external_fault) fault(32'h200);
   // Sticky fault has final priority over every new successful completion.
   if(error_status || cycle_errors) begin
    error_status<=error_status|cycle_errors;retire_valid<=0;busy<=1;
   end
  end
 end
endmodule
