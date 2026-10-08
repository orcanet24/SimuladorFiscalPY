package simulator_test

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"

	"simuladorfiscal/internal/simulator"
)

type scenario struct {
	name     string
	commands []string
}

type goldenRecord struct {
	Scenario string `json:"scenario"`
	I        int    `json:"i"`
	Command  string `json:"command"`
	Response string `json:"response"`
}

var tsRe = regexp.MustCompile(`\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}`)

func normalizeTS(s string) string {
	return tsRe.ReplaceAllString(s, "<TS>")
}

var tfhkaCorpus = []scenario{
	{"invoice_full", []string{
		"iR*J-12345678-9",
		"iS*EMPRESA DE PRUEBA C.A.",
		"i01Av. Principal, Caracas",
		"i020414-1234567",
		"!   1.000     15.00 CAFE",
		"\"   2.000      8.00 PAN",
		"#   1.000   1000.00 LICORES",
		"3",
		"1002031.00",
		"101",
		"S1",
		"U0X",
		"U0Z",
	}},
	{"credit_note", []string{
		"iR*J-12345678-9",
		"iS*EMPRESA C.A.",
		"!   1.000     15.00 CAFE",
		"10015.00",
		"101",
		"d1",
		"iR*J-12345678-9",
		"iS*EMPRESA C.A.",
		"iF*001",
		"iD*2024-01-15",
		"iI*MLTFHKA001",
		"d1   1.000     15.00 CAFE",
		"101",
		"S2",
	}},
	{"debit_note", []string{
		"d2",
		"iR*J-12345678-9",
		"iF*002",
		"`1   1.000     15.00 CAFE",
		"101",
		"S2",
	}},
	{"non_fiscal", []string{
		"80$",
		"80!PRESUPUESTO",
		"80*Linea de texto libre",
		"81",
	}},
	{"status_suite", []string{
		"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8E", "S8P",
	}},
	{"payments_discounts", []string{
		"!   1.000    100.00 SERVICIO",
		"70010.00",
		"7015.00",
		"103Pago parcial",
		"10050.00",
		"S4",
		"S2",
		"101",
	}},
	{"drawer_comment", []string{
		"0",
		"@COMENTARIO una nota",
		"4",
	}},
	{"reports_x2_z2", []string{
		"!   1.000     20.00 TE",
		"10020.00",
		"101",
		"U1X",
		"U1Z",
	}},
	{"exempt_quirk", []string{
		"    1.000     10.00 EXENTO",
	}},
	{"runes_desc", []string{
		"iS*NIÑO & ASOC.",
		"!   1.000     15.00 CAFÉ ÑUÑOÁ",
		"101",
	}},
	{"errors_edge", []string{
		"",
		"   ",
		"FOO",
		"!",
		"!   x.000     15.00 BAD",
		"d1",
		"d1short",
		"`x",
		"100abc",
		"100",
		"700",
		"701",
		"iR*",
		"iS*",
		"i01",
		"iF*",
		"iD*",
		"iI*",
		"@Foo|bar",
		"81",
		"3",
		"101",
		"0",
	}},
}

var ixbatchCorpus = []scenario{
	{"full_flow", []string{
		"@CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal",
		"@OpenFiscalReceipt",
		"@PrintLine|Cafe|2|15.00|general",
		"@PrintLine|Pan|3|8.00|reduced",
		"@Subtotal",
		"@AddPayment|100.00|cash",
		"@Close",
		"@Status",
		"@PrintZReport",
	}},
	{"cross_status", []string{
		"@OpenFiscalReceipt",
		"@PrintLine|Item1|1|100.00|general",
		"@AddPayment|116.00|cash",
		"@Close",
		"S1",
		"S2",
		"S3",
		"S5",
		"S8E",
		"U0X",
		"@PrintZReport",
	}},
	{"credit_debit_notes", []string{
		"@OpenCreditNote",
		"@CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal",
		"@PrintLine|Devolucion|1|15.00|general",
		"@Close",
		"@OpenDebitNote",
		"@PrintLine|Recargo|1|10.00|general",
		"@Close",
		"S2",
	}},
	{"non_fiscal", []string{
		"@OpenNonFiscalDoc",
		"@PrintNonFiscalText|Hola",
		"@PrintFiscalText|Texto fiscal",
		"@CloseNonFiscalDoc",
	}},
	{"customer_variants", []string{
		"@CustomerData|J-1|NOMBRE|DIRECCION",
		"@CustomerData|J-2|SOLO NOMBRE",
		"@CustomerData|J-3",
		"@SetCustomerData|J-4|CLASICO",
		"@SetCustomerTIN|J-555",
		"@SetCustomerInfo1|NOMBRE 1",
		"@SetCustomerInfo2|NOMBRE 2",
		"@SetCustomerExtraData|extra=1",
		"@CustomerData|||",
	}},
	{"tax_specs", []string{
		"@OpenFiscalReceipt",
		"@PrintLine|A|1|10|0",
		"@PrintLine|B|1|10|1",
		"@PrintLine|C|1|10|2",
		"@PrintLine|D|1|10|3",
		"@PrintLine|E|1|10|16",
		"@PrintLine|F|1|10|8",
		"@PrintLine|G|1|10|30",
		"@PrintLine|H|1|10|99",
		"@PrintLine|I|1|10|exento",
		"@PrintLine|J|1|10|reducida",
		"@PrintLine|K|1|10|",
		"@PrintLine|L|1|10",
		"@PrintLine|M|1|10|general|Q",
		"@PrintLineItem|N|1|10|general|M",
		"@RefundItem|R|1|10|general",
		"@Close",
	}},
	{"payments_flow", []string{
		"@OpenFiscalReceipt",
		"@PrintLine|Cafe|1|30.00|general",
		"@Subtotal",
		"@AddPayment|30.00|tarjeta",
		"@AddPayment|5.50|efectivo",
		"@TotalTender|Efectivo|0|T|0",
		"@LastItemCancel",
		"@LastItemDiscount|5.00|X",
		"@Status",
		"@Close",
		"@PrintXReport",
		"@PrintZReport",
		"@DailyClose|Z",
		"@DailyCloseByDate",
		"@DailyCloseByNumber",
		"@RefundClose|10.00|1",
	}},
	{"misc_ack", []string{
		"@OpenDrawer",
		"@OpenDrawer|2",
		"@BarCode|12345",
		"@Login|cajero",
		"@Logoff",
		"@PrintTest",
		"@Reprint",
		"@ReprintByDate|2024-01-01",
		"@ReprintByNumber|1",
		"@SetDate|2024-01-01",
		"@SetTime|10:00:00",
		"@StatusExtra",
		"@ConfigureControllerByOne",
		"@PrintConfigurationData",
		"@ProgramClerk|1",
		"@ProgramPaymentMedia|cash",
		"@ProgramSymbol|Bs.",
		"@ProgramTaxes|16|8|30",
		"@SaveTaxes",
		"@SendRawCommand|raw",
		"@SetHeaderTrailer|H|T",
		"@DisplayCommercial|COMERCIAL",
		"@DisplayDateTime",
		"@DisplayMessage|MSG",
		"@ProgramCommercial|COM",
		"@ProgramMessage|MSG",
		"@FormatCheck|1",
		"@FormatEndorse|1",
		"@ModeSlip",
		"@ModeValidation",
		"@PrintEndorse",
		"@PrintValidation",
		"@ReadMICR",
		"@PrintCashItem",
		"@PrintAuditStatusReport",
		"@TrainingMode",
		"@ResetPrinterBuffer",
		"@CloseFiscalReceipt",
		"@CloseCashReceipt",
		"@DailyClose",
		"@Cancel",
		"@AddPayment|10|cash",
		"@Subtotal",
		"@Status",
	}},
	{"errors_edge", []string{
		"@PrintLine|d|x|y",
		"@PrintLine|d|1",
		"@PrintLine",
		"@AddPayment|abc|cash",
		"@AddPayment",
		"@Foo|bar",
		"@",
		"@RefundItem|d|1|10|general",
		"@TotalTender|solo",
		"@DirectPayment",
		"@DirectPayment|x",
		"@RefundClose|10",
		"@DailyCloseX",
		"@Status|extra",
		"S1",
		"U0Z",
		"101",
		"3",
		"",
	}},
}

func goldenDir(t *testing.T) string {
	t.Helper()
	dir := filepath.Join("..", "..", "testdata", "golden")
	if _, err := os.Stat(dir); err != nil {
		t.Fatalf("golden dir missing: %v", err)
	}
	return dir
}

func joinLines(lines []string) string {
	var b strings.Builder
	for _, l := range lines {
		b.WriteString(l)
		b.WriteString("\n")
	}
	return b.String()
}

func compareGolden(t *testing.T, name string, got []string) {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(goldenDir(t), name))
	if err != nil {
		t.Fatalf("read %s: %v", name, err)
	}
	want := string(data)
	gotStr := joinLines(got)
	if gotStr == want {
		return
	}
	wantLines := []string{}
	if want != "" {
		wantLines = strings.Split(strings.TrimSuffix(want, "\n"), "\n")
	}
	n := len(wantLines)
	if len(got) > n {
		n = len(got)
	}
	for i := 0; i < n; i++ {
		var w, g string
		if i < len(wantLines) {
			w = wantLines[i]
		}
		if i < len(got) {
			g = got[i]
		}
		if w != g {
			t.Errorf("%s line %d:\n got: %q\nwant: %q", name, i+1, g, w)
			return
		}
	}
	t.Errorf("%s: line count got %d, want %d", name, len(got), len(wantLines))
}

func readGoldenJSONL(t *testing.T, name string) []goldenRecord {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(goldenDir(t), name))
	if err != nil {
		t.Fatalf("read %s: %v", name, err)
	}
	var recs []goldenRecord
	dec := json.NewDecoder(bytes.NewReader(data))
	for dec.More() {
		var r goldenRecord
		if err := dec.Decode(&r); err != nil {
			t.Fatalf("decode %s: %v", name, err)
		}
		recs = append(recs, r)
	}
	return recs
}

func TestCommandsGolden(t *testing.T) {
	corpora := map[string][]scenario{
		"tfhka":   tfhkaCorpus,
		"hasar":   ixbatchCorpus,
		"bixolon": ixbatchCorpus,
		"epson":   ixbatchCorpus,
	}
	for brand, corpus := range corpora {
		t.Run(brand, func(t *testing.T) {
			golden := readGoldenJSONL(t, "commands_"+brand+".jsonl")
			idx := 0
			for _, sc := range corpus {
				sim, err := simulator.CreateSimulator(brand, "", "")
				if err != nil {
					t.Fatalf("create: %v", err)
				}
				for i, cmd := range sc.commands {
					got := sim.ProcessCommand(cmd)
					if idx >= len(golden) {
						t.Fatalf("extra response %s/%d", sc.name, i)
					}
					rec := golden[idx]
					idx++
					if rec.Scenario != sc.name || rec.I != i || rec.Command != cmd {
						t.Fatalf("golden misaligned at %d: got scenario=%q i=%d cmd=%q, golden=%q %d %q",
							idx-1, sc.name, i, cmd, rec.Scenario, rec.I, rec.Command)
					}
					want := rec.Response
					if norm := normalizeTS(got); norm != want {
						t.Errorf("%s[%d] %q:\n got: %q\nwant: %q", sc.name, i, cmd, norm, want)
					}
				}
			}
			if idx != len(golden) {
				t.Errorf("golden has %d extra records (consumed %d of %d)", len(golden)-idx, idx, len(golden))
			}
		})
	}
}
