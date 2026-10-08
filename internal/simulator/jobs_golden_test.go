package simulator_test

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"

	"simuladorfiscal/internal/render"
	"simuladorfiscal/internal/simulator"
)

var paperTSRe = regexp.MustCompile(`\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}`)

func normalizePaper(s string) string {
	return paperTSRe.ReplaceAllString(s, "<TS>")
}

type jobFlow struct {
	brand    string
	scenario string
	commands []string
}

var jobFlows = []jobFlow{
	{"tfhka", "invoice_x_z", []string{
		"iR*J-12345678-9",
		"iS*EMPRESA C.A.",
		"i01Av. Principal, Caracas",
		"!   1.000     15.00 CAFE",
		"\"   2.000      8.00 PAN",
		"3",
		"10031.00",
		"101",
		"U0X",
		"U0Z",
	}},
	{"tfhka", "credit_note", []string{
		"d1",
		"iR*J-12345678-9",
		"iF*001",
		"iD*2024-01-15",
		"iI*MLTFHKA001",
		"d1   1.000     15.00 CAFE",
		"101",
	}},
	{"tfhka", "debit_note", []string{
		"d2",
		"`1   1.000     15.00 CAFE",
		"101",
	}},
	{"tfhka", "non_fiscal", []string{
		"80$",
		"80!PRESUPUESTO",
		"81",
	}},
	{"hasar", "invoice_x_z", []string{
		"@CustomerData|J-12345678-9|EMPRESA C.A.|Av Principal",
		"@OpenFiscalReceipt",
		"@PrintLine|Cafe|2|15.00|general",
		"@PrintLine|Pan|3|8.00|reduced",
		"@Subtotal",
		"@AddPayment|100.00|cash",
		"@Close",
		"@PrintXReport",
		"@PrintZReport",
	}},
	{"bixolon", "invoice", []string{
		"@OpenFiscalReceipt",
		"@PrintLine|Item1|1|100.00|general",
		"@AddPayment|116.00|cash",
		"@Close",
	}},
	{"epson", "invoice", []string{
		"@OpenFiscalReceipt",
		"@PrintLine|Item1|1|500.00|general",
		"@AddPayment|580.00|cash",
		"@Close",
		"@PrintZReport",
	}},
}

func TestPaperJobsGolden(t *testing.T) {
	for _, brand := range []string{"tfhka", "hasar", "bixolon", "epson"} {
		t.Run(brand, func(t *testing.T) {
			var gotLines []string
			for _, flow := range jobFlows {
				if flow.brand != brand {
					continue
				}
				sim, err := simulator.CreateSimulator(brand, "", "")
				if err != nil {
					t.Fatalf("create: %v", err)
				}
				for _, cmd := range flow.commands {
					sim.ProcessCommand(cmd)
				}
				for _, job := range sim.State.PrintJobs {
					tag := fmt.Sprintf("%s/%s/%d", flow.scenario, job.Kind, job.ID)
					for _, line := range job.Lines {
						gotLines = append(gotLines, tag+"\t"+normalizePaper(line))
					}
				}
			}
			data, err := os.ReadFile(filepath.Join(goldenDir(t), "paper_jobs_"+brand+".jsonl"))
			if err != nil {
				t.Fatalf("read golden: %v", err)
			}
			want := string(data)
			wantLines := []string{}
			if want != "" {
				wantLines = strings.Split(strings.TrimSuffix(want, "\n"), "\n")
			}
			if len(gotLines) != len(wantLines) {
				t.Errorf("line count got %d, want %d", len(gotLines), len(wantLines))
			}
			n := len(wantLines)
			if len(gotLines) < n {
				n = len(gotLines)
			}
			for i := 0; i < n; i++ {
				if gotLines[i] != wantLines[i] {
					t.Errorf("line %d:\n got: %q\nwant: %q", i+1, gotLines[i], wantLines[i])
					return
				}
			}
		})
	}
}

func TestPreviewGolden(t *testing.T) {
	sim, err := simulator.CreateSimulator("tfhka", "", "")
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	sim.ProcessCommand("iR*J-99999999-9")
	sim.ProcessCommand("iS*CLIENTE EN CURSO")
	sim.ProcessCommand("!   1.000     15.00 CAFE")
	sim.ProcessCommand("10015.00")

	lines := render.RenderOpenDocument(sim.State)
	normalized := make([]string, 0, len(lines))
	for _, l := range lines {
		normalized = append(normalized, normalizePaper(l))
	}
	compareGolden(t, "paper_fixed_preview.txt", normalized)

	sim.ProcessCommand("101")
	closed := render.RenderOpenDocument(sim.State)
	compareGolden(t, "paper_fixed_preview_closed.txt", closed)
}
