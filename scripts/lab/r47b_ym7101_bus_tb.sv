// R47B-RTL stage 1: actual pinned Nuked YM7101 clock/reset smoke and VCD.
// NOT yet VDP register protocol, VBlank DMA or full-MD bus timing.
`timescale 1ns/1ps

module r47b_ym7101_bus;
  reg MCLK=0, RESET=0;
  reg [22:0] cpu_addr=23'h7fffff;
  reg [15:0] cpu_data=16'hffff;
  reg cpu_as_n=1, cpu_uds_n=1, cpu_lds_n=1, cpu_rw_n=1;
  reg cpu_sel=1'b1;

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
    .SEL0(cpu_sel),.CLK1_i(1'b0),.CLK1_o(CLK1_o),
    .SBCR(SBCR),.CLK0(CLK0),.CLK1_next(CLK1_next),.CLK0_next(CLK0_next),
    .MCLK_e(MCLK_e),.EDCLK_i(1'b0),.EDCLK_o(EDCLK_o),.EDCLK_d(EDCLK_d),
    .CD_i(cpu_data),.CD_o(CD_o),.CD_d(CD_d),
    .CA_i(cpu_addr),.CA_o(CA_o),.CA_d(CA_d),.SOUND(SOUND),
    .INT_pull(INT_pull),.BR_pull(BR_pull),.BGACK_i(1'b1),
    .BGACK_pull(BGACK_pull),.BG(1'b1),.MREQ(1'b1),
    .INTAK(1'b1),.IPL1_pull(IPL1_pull),.IPL2_pull(IPL2_pull),
    .IORQ(1'b1),.RD(1'b1),.WR(1'b1),.M1(1'b1),
    .AS(cpu_as_n),.UDS(cpu_uds_n),.LDS(cpu_lds_n),.RW(cpu_rw_n),
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

  integer register_write_pulses=0, m5_seen=0, cpu_write_windows=0;
  always @(posedge MCLK) begin
    if(RESET && dut.w217===1'b1) register_write_pulses<=register_write_pulses+1;
    if(RESET && dut.reg_m5===1'b1) m5_seen<=m5_seen+1;
    if(RESET && dut.cpu_as===1'b1 && dut.cpu_rw===1'b1) cpu_write_windows<=cpu_write_windows+1;
  end

  // Deliberately conservative 68000-like strobe: address/data stable
  // before /AS and /UDS /LDS, held across many CPU clock phases.
  // This is not a complete 68000 timing or DTACK handshake model.
  task write_vdp;
    input [22:0] address;
    input [15:0] data;
    begin
      @(negedge MCLK);
      cpu_addr=address; cpu_data=data; cpu_rw_n=1'b0;
      repeat(32) @(negedge MCLK);
      cpu_as_n=1'b0; cpu_uds_n=1'b0; cpu_lds_n=1'b0;
      repeat(112) @(negedge MCLK);
      cpu_as_n=1'b1; cpu_uds_n=1'b1; cpu_lds_n=1'b1;
      repeat(64) @(negedge MCLK);
      cpu_rw_n=1'b1;
    end
  endtask

  initial begin
    $dumpfile("dist/r47b-rtl/r47b_ym7101_bus.vcd");
    $dumpvars(0,r47b_ym7101_bus);
    repeat(128) @(negedge MCLK);
    RESET=1'b1;
    repeat(5000) @(negedge MCLK);
    $display("R47B_BUS before reg_m5=%b reg_81_b0=%b reg_81_b1=%b",dut.reg_m5,dut.reg_81_b0,dut.reg_81_b1);
    // VDP register 1 (mode set 2) = 0x04 (M5). 68k byte address C00004,
    // represented on 23-bit 68k address lines A23..A1 as 0x600002.
    write_vdp(23'h600002,16'h8104);
    repeat(3000) @(negedge MCLK);
    $display("R47B_BUS after reg_m5=%b reg_81_b0=%b reg_81_b1=%b write_pulses=%0d m5_seen=%0d cpu_write_windows=%0d io_data=%h reg_data_l2=%h",
      dut.reg_m5,dut.reg_81_b0,dut.reg_81_b1,register_write_pulses,m5_seen,cpu_write_windows,dut.io_data,dut.reg_data_l2);
    if(cpu_write_windows<30) $fatal(1,"FAIL: CPU bus strobe not observed in RTL");
    if(dut.reg_m5!==1'b1 || register_write_pulses==0)
      $fatal(1,"FAIL: VDP mode register did not latch through real 68000-like bus");
    $display("PASS: VDP mode register write observed through external bus; DMA not yet exercised");
    $finish;
  end
endmodule
