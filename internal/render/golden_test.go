package render_test

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	"simuladorfiscal/internal/orderedmap"
	"simuladorfiscal/internal/render"
	"simuladorfiscal/internal/state"
)

func goldenPath(name string) string {
	return filepath.Join("..", "..", "testdata", "golden", name)
}

func readGolden(t *testing.T, name string) string {
	t.Helper()
	data, err := os.ReadFile(goldenPath(name))
	if err != nil {
		t.Fatalf("read %s: %v", name, err)
	}
	return string(data)
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
	want := readGolden(t, name)
	gotStr := joinLines(got)
	if gotStr == want {
		return
	}
	wantLines := strings.Split(strings.TrimSuffix(want, "\n"), "\n")
	if want == "" {
		wantLines = nil
	}
	gotLines := got
	n := len(wantLines)
	if len(gotLines) > n {
		n = len(gotLines)
	}
	for i := 0; i < n; i++ {
		var w, g string
		if i < len(wantLines) {
			w = wantLines[i]
		}
		if i < len(gotLines) {
			g = gotLines[i]
		}
		if w != g {
			t.Errorf("%s line %d:\n got: %q\nwant: %q", name, i+1, g, w)
			return
		}
	}
	t.Errorf("%s: line count got %d, want %d", name, len(gotLines), len(wantLines))
}

var fixedTS = time.Date(2026, 1, 15, 10, 30, 0, 0, time.UTC)

var testCompany = state.Company{
	Rif:                   "J-12345678-9",
	RazonSocial:           "COMERCIAL LOS SIMULADORES C.A.",
	Direccion:             "Avenida Principal de Los Chaguaramos, Edificio Fiscal, Piso 4, Oficina B",
	Municipio:             "CHACAO",
	Ciudad:                "CARACAS",
	Estado:                "MIRANDA",
	Telefono:              "0212-9555123",
	Email:                 "facturacion@simuladores.com.ve",
	RepresentanteLegal:    "JUAN PEREZ RODRIGUEZ",
	CedulaRepresentante:   "V-12345678",
	ActividadEconomica:    "VENTA DE EQUIPOS DE OFICINA Y SUMINISTROS",
	Nif:                   "",
	Moneda:                "Bs.",
	LogoText:              "LOS SIMULADORES",
	CondicionesPago:       "CONTADO 30 DIAS",
	ContribuyenteEspecial: true,
	AgenteRetencion:       true,
}

func baseDoc() state.Document {
	return state.Document{
		Type:         "invoice",
		Number:       42,
		Timestamp:    state.PyTime{Time: fixedTS},
		SerialNumber: "MLTFHKA001",
		Rif:          "J-12345678-9",
		Company:      testCompany,
		Payments:     orderedmap.New[string, float64](),
	}
}

var creditNoteItems = []state.Item{{
	Description: "CAFE", Quantity: 1, Price: 15.0,
	TaxType: "general", TaxRate: 16.0,
	Base: 12.931034482758621, Tax: 2.0689655172413794, Total: 15.0,
}}

func TestFixedReceipt(t *testing.T) {
	doc := baseDoc()
	doc.Items = []state.Item{
		{Description: "CAFE EXCLUSIVO DE VENEZUELA", Quantity: 2, Price: 15.5,
			TaxType: "general", TaxRate: 16.0,
			Base: 26.724137931034484, Tax: 3.2758620689655172, Total: 31.0},
		{Description: "PAN", Quantity: 3, Price: 8.0,
			TaxType: "reduced", TaxRate: 8.0,
			Base: 22.22222222222222, Tax: 1.7777777777777777, Total: 24.0},
		{Description: "LICORES FINOS", Quantity: 1, Price: 100.0,
			TaxType: "additional", TaxRate: 30.0,
			Base: 76.92307692307692, Tax: 23.076923076923077, Total: 100.0},
		{Description: "PAN EXENTO", Quantity: 1, Price: 5.0,
			TaxType: "exempt", TaxRate: 0.0,
			Base: 5.0, Tax: 0.0, Total: 5.0},
	}
	doc.SubtotalBases = 130.86943707633362
	doc.SubtotalTax = 28.13056292366648
	doc.Total = 159.0
	doc.Customer = state.Customer{
		Rif:     "V-12345678",
		Name:    "MARIA GARCIA DE LOPEZ",
		Address: "Calle El Sol, Qta La Esperanza, Urb Las Flores",
	}
	doc.Payments.Set("cash", 200.0)
	doc.Payments.Set("card", 0.0)
	doc.Paid = 200.0
	doc.Change = 41.0
	compareGolden(t, "paper_fixed_receipt.txt", render.RenderReceipt(&doc, testCompany))
}

func TestFixedCreditNote(t *testing.T) {
	doc := baseDoc()
	doc.Type = "credit_note"
	doc.Number = 7
	doc.Items = creditNoteItems
	doc.SubtotalBases = 12.931034482758621
	doc.SubtotalTax = 2.0689655172413794
	doc.Total = 15.0
	doc.Payments.Set("cash", 15.0)
	doc.Paid = 15.0
	doc.ReferenceInvoice = "00000041"
	doc.ReferenceDate = "2026-01-10"
	doc.ReferenceSerial = "MLTFHKA001"
	compareGolden(t, "paper_fixed_credit.txt", render.RenderReceipt(&doc, testCompany))
}

func TestFixedDebitNote(t *testing.T) {
	doc := baseDoc()
	doc.Type = "debit_note"
	doc.Number = 3
	doc.Items = creditNoteItems
	doc.SubtotalBases = 12.931034482758621
	doc.SubtotalTax = 2.0689655172413794
	doc.Total = 15.0
	doc.Payments.Set("transfer", 15.0)
	doc.Paid = 15.0
	doc.ReferenceInvoice = "00000040"
	compareGolden(t, "paper_fixed_debit.txt", render.RenderReceipt(&doc, testCompany))
}

func TestFixedConsumer(t *testing.T) {
	doc := baseDoc()
	doc.Items = []state.Item{{
		Description: "ITEM", Quantity: 1, Price: 10.0,
		TaxType: "general", TaxRate: 16.0,
		Base: 8.620689655172413, Tax: 1.3793103448275863, Total: 10.0,
	}}
	doc.SubtotalBases = 8.620689655172413
	doc.SubtotalTax = 1.3793103448275863
	doc.Total = 10.0
	doc.Payments.Set("cash", 10.0)
	doc.Paid = 10.0
	compareGolden(t, "paper_fixed_consumer.txt", render.RenderReceipt(&doc, testCompany))
}

func TestFixedNonFiscal(t *testing.T) {
	doc := baseDoc()
	doc.Type = "non_fiscal"
	doc.Number = 9
	doc.Items = []state.Item{
		{Description: "PRESUPUESTO DE OBRA NRO 9"},
		{Description: "Linea muy larga de texto no fiscal que debe envolverse en varias lineas de papel"},
		{Description: "Total estimado: Bs. 1.500,00"},
	}
	compareGolden(t, "paper_fixed_nonfiscal.txt", render.RenderNonFiscal(&doc, testCompany))
}

func baseReport() state.Report {
	rep := state.Report{
		Type:             "X",
		Number:           12,
		Timestamp:        state.PyTime{Time: fixedTS},
		LastInvoice:      42,
		LastCreditNote:   7,
		LastDebitNote:    3,
		TotalSales:       159.0,
		TotalTax:         28.13,
		DailyInvoices:    5,
		DailyCreditNotes: 1,
		DailyDebitNotes:  1,
		DailyNonFiscal:   2,
		TaxTotals: map[string]state.TaxBlock{
			"general":    {Base: 60.0, Tax: 9.6},
			"reduced":    {Base: 40.0, Tax: 3.2},
			"additional": {Base: 50.0, Tax: 15.0},
			"exempt":     {Base: 0.0, Tax: 0.0},
		},
		Payments: orderedmap.New[string, float64](),
	}
	rep.Payments.Set("cash", 100.0)
	rep.Payments.Set("card", 59.0)
	rep.Payments.Set("transfer", 0.0)
	return rep
}

func TestFixedXReport(t *testing.T) {
	rep := baseReport()
	compareGolden(t, "paper_fixed_xreport.txt", render.RenderXReport(&rep, testCompany))
}

func TestFixedZReport(t *testing.T) {
	rep := baseReport()
	rep.Type = "Z"
	rep.Number = 13
	rep.TotalDiscounts = 5.0
	rep.TotalSurcharges = 2.5
	compareGolden(t, "paper_fixed_zreport.txt", render.RenderZReport(&rep, testCompany))
}

func TestFixedEmptyXReport(t *testing.T) {
	rep := state.Report{
		Type:      "X",
		Number:    1,
		Timestamp: state.PyTime{Time: fixedTS},
		TaxTotals: map[string]state.TaxBlock{
			"general":    {},
			"reduced":    {},
			"additional": {},
			"exempt":     {},
		},
		Payments: orderedmap.New[string, float64](),
	}
	compareGolden(t, "paper_fixed_empty_x.txt", render.RenderXReport(&rep, testCompany))
}

func TestFixedBareCompany(t *testing.T) {
	empty := state.Company{}
	doc := baseDoc()
	doc.Items = []state.Item{{
		Description: "X", Quantity: 1, Price: 1.0,
		TaxType: "general", TaxRate: 16.0,
		Base: 0.8620689655172413, Tax: 0.13793103448275863, Total: 1.0,
	}}
	doc.SubtotalBases = 0.8620689655172413
	doc.SubtotalTax = 0.13793103448275863
	doc.Total = 1.0
	doc.Company = empty
	compareGolden(t, "paper_fixed_bare_company.txt", render.RenderReceipt(&doc, empty))
}

func TestWordsGolden(t *testing.T) {
	data := readGolden(t, "words.txt")
	lines := strings.Split(strings.TrimSuffix(data, "\n"), "\n")
	if data == "" {
		t.Fatal("words.txt empty")
	}
	for i, line := range lines {
		parts := strings.SplitN(line, "\t", 2)
		if len(parts) != 2 {
			t.Fatalf("line %d: %q", i+1, line)
		}
		amount, err := strconv.ParseFloat(parts[0], 64)
		if err != nil {
			t.Fatalf("line %d: parse %q: %v", i+1, parts[0], err)
		}
		got := render.NumberToWords(amount)
		if got != parts[1] {
			t.Errorf("NumberToWords(%s):\n got: %q\nwant: %q", parts[0], got, parts[1])
		}
	}
}
