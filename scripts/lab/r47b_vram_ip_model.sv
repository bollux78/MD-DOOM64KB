// R47B simulation-only functional stand-in for MiSTer vram_ip (FPGA RAM IP).
// 256 addresses x 256 bits; 32 byte enables. No FPGA timing/analog model.
// Used ONLY with upstream pinned rtl/nuked-md/vram.v in Icarus.
module vram_ip(
  input clock,
  input [7:0] address,
  input [31:0] byteena,
  input [255:0] data,
  input wren,
  output reg [255:0] q
);
  reg [255:0] mem[0:255];
  integer write_count=0;
  integer unique_count=0;
  integer wrong_pattern_count=0;
  reg [31:0] touched[0:255];
  integer a,b;
  initial begin
    q=0;
    for(a=0;a<256;a=a+1) begin mem[a]=0; touched[a]=0; end
  end
  task automatic reset_stats;
    integer k;
    begin
      write_count=0;
      unique_count=0;
      wrong_pattern_count=0;
      for(k=0;k<256;k=k+1) touched[k]=0;
    end
  endtask
  always @(posedge clock) begin
    q<=mem[address];
    if(wren) for(b=0;b<32;b=b+1) begin
      if(byteena[b]) begin
        mem[address][8*b+:8]<=data[8*b+:8];
        write_count<=write_count+1;
        if(touched[address][b]!==1'b1) begin
          touched[address][b]<=1'b1;
          unique_count<=unique_count+1;
        end
        if(data[8*b+:8] !== ((b%2==0)?8'h5a:8'ha5))
          wrong_pattern_count<=wrong_pattern_count+1;
      end
    end
  end
endmodule
