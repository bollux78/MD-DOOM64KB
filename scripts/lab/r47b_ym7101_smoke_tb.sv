// R47B-RTL stage 1: actual pinned Nuked YM7101 clock/reset smoke and VCD.
// NOT yet VDP register protocol, VBlank DMA or full-MD bus timing.
`timescale 1ns/1ps

module r47b_ym7101_smoke;
  reg MCLK=0, RESET=0;
  reg MCLK_e=0;
  always @(posedge MCLK) MCLK_e <= ~MCLK_e; // matches md_board.v
  always #9.313 MCLK=~MCLK; // approx NTSC 53.69 MHz oscillator
  wire vdp_hclk1,vdp_de_h,vdp_de_v,vdp_dma,vdp_dma_oe_early;
  wire vdp_hsync2,vdp_vsync2,VSYNC;
  wire [7:0] DAC_R,DAC_G,DAC_B;
  wire [7:0] AD_o,RD_o;
  wire AD_d,RD_d;
  wire [15:0] CD_o;
  wire CD_d;
  wire [22:0] CA_o;
  wire CA_d;
  wire [7:0] RA;
  wire [15:0] SOUND;
  wire CLK0,CLK1_next,CLK0_next,SBCR,CLK1_o;
  wire SE1,SE0,SC,RAS1,CAS1,WE1,WE0,OE1,YS;
  wire SPA_B_pull,CSYNC_pull,HSYNC_pull;
  wire INT_pull,BR_pull,BGACK_pull,IPL1_pull,IPL2_pull,DTACK_pull;
  wire UWR,LWR,OE0,CAS0,RAS0,vdp_intfield,vdp_m5,vdp_rs1,vdp_m2,vdp_lcb,vdp_psg_clk1;
  wire EDCLK_o,EDCLK_d;

  // Idle 68000 bus with all active-low strobes deasserted.
  // CD_i / CA_i are NOT a functional DMA cartridge memory model here.
  ym7101 dut(
    .MCLK(MCLK),.RESET(RESET),.PAL(1'b0),.HL(1'b0),
    .SD(8'h00),.SE1(SE1),.SE0(SE0),.SC(SC),
    .RAS1(RAS1),.CAS1(CAS1),.WE1(WE1),.WE0(WE0),.OE1(OE1),
    .RD_i(8'h00),.RD_o(RD_o),.RD_d(RD_d),
    .DAC_R(DAC_R),.DAC_G(DAC_G),.DAC_B(DAC_B),
    .AD_i(8'h00),.AD_o(AD_o),.AD_d(AD_d),.YS(YS),
    .SPA_B_i(1'b1),.SPA_B_pull(SPA_B_pull),.VSYNC(VSYNC),
    .CSYNC_i(1'b1),.CSYNC_pull(CSYNC_pull),
    .HSYNC_i(1'b1),.HSYNC_pull(HSYNC_pull),
    .SEL0(1'b0),.CLK1_i(1'b0),.CLK1_o(CLK1_o),
    .SBCR(SBCR),.CLK0(CLK0),.CLK1_next(CLK1_next),.CLK0_next(CLK0_next),
    .MCLK_e(MCLK_e),.EDCLK_i(1'b0),.EDCLK_o(EDCLK_o),.EDCLK_d(EDCLK_d),
    .CD_i(16'hFFFF),.CD_o(CD_o),.CD_d(CD_d),
    .CA_i(23'h7FFFFF),.CA_o(CA_o),.CA_d(CA_d),.SOUND(SOUND),
    .INT_pull(INT_pull),.BR_pull(BR_pull),.BGACK_i(1'b1),
    .BGACK_pull(BGACK_pull),.BG(1'b1),.MREQ(1'b1),
    .INTAK(1'b1),.IPL1_pull(IPL1_pull),.IPL2_pull(IPL2_pull),
    .IORQ(1'b1),.RD(1'b1),.WR(1'b1),.M1(1'b1),
    .AS(1'b1),.UDS(1'b1),.LDS(1'b1),.RW(1'b1),
    .DTACK_i(1'b1),.DTACK_pull(DTACK_pull),
    .UWR(UWR),.LWR(LWR),.OE0(OE0),.CAS0(CAS0),.RAS0(RAS0),.RA(RA),
    .ext_test_2(1'b0),.vdp_hclk1(vdp_hclk1),.vdp_intfield(vdp_intfield),
    .vdp_de_h(vdp_de_h),.vdp_de_v(vdp_de_v),.vdp_m5(vdp_m5),
    .vdp_rs1(vdp_rs1),.vdp_m2(vdp_m2),.vdp_lcb(vdp_lcb),
    .vdp_psg_clk1(vdp_psg_clk1),.vdp_hsync2(vdp_hsync2),
    .vdp_vsync2(vdp_vsync2),.vdp_cramdot_dis(1'b0),
    .vdp_dma_oe_early(vdp_dma_oe_early),.vdp_dma(vdp_dma)
  );

  integer mcycles=0,hclk_edges=0,vdma_high=0;
  integer known_clock=0;
  integer dma_after_reset=0;
  integer de_h_known=0;
  integer de_v_known=0;
  integer dma_unknown=0;
  reg old_hclk=0;
  always @(posedge MCLK) begin
    mcycles<=mcycles+1;
    if(vdp_hclk1!==1'bx && vdp_hclk1!==1'bz)
      known_clock<=known_clock+1;
    if(old_hclk===1'b0 && vdp_hclk1===1'b1) hclk_edges<=hclk_edges+1;
    old_hclk<=vdp_hclk1;
    if(vdp_dma===1'b1) begin
      vdma_high<=vdma_high+1;
      if(RESET===1'b1) dma_after_reset<=dma_after_reset+1;
    end
    if(vdp_dma===1'bx || vdp_dma===1'bz) dma_unknown<=dma_unknown+1;
    if(vdp_de_h===1'b0 || vdp_de_h===1'b1) de_h_known<=de_h_known+1;
    if(vdp_de_v===1'b0 || vdp_de_v===1'b1) de_v_known<=de_v_known+1;
  end
  initial begin
    $dumpfile("dist/r47b-rtl/r47b_ym7101_smoke.vcd");
    $dumpvars(0,r47b_ym7101_smoke);
    repeat(128) @(negedge MCLK);
    RESET=1'b1; // reset pin is active-low in YM7101 source
    repeat(12000) @(negedge MCLK);
    $display("R47B_SMOKE master_clocks=%0d hclk_posedges=%0d clock_known=%0d dma_active_clocks=%0d",
             mcycles,hclk_edges,known_clock,vdma_high);
    $display("R47B_DIAG dma_after_reset=%0d dma_unknown=%0d de_h_known=%0d de_v_known=%0d cpu_sel=%b reset_comb=%b",dma_after_reset,dma_unknown,de_h_known,de_v_known,dut.cpu_sel,dut.reset_comb);
    if(known_clock<3000 || hclk_edges<100) begin
      $display("FAIL: VDP clock outputs not cycling");
      $fatal(1);
    end
    if(dma_after_reset!=0) begin
      $display("WARN: DMA active after reset deassertion during idle (investigate)"); 
    end
    $display("PASS: real RTL clock/reset activity observed; DMA transfers NOT exercised");
    $finish;
  end
endmodule
