package state

import (
	"encoding/json"
	"fmt"
	"time"

	"simuladorfiscal/internal/orderedmap"
	"simuladorfiscal/internal/pyfmt"
)

func (s *State) CalculateItemTax(price, taxRate float64) (float64, float64) {
	var base, tax float64
	if s.TaxType == 1 {
		base = price / (1 + taxRate/100)
		tax = price - base
	} else {
		base = price
		tax = price * taxRate / 100
	}
	return base, tax
}

func (s *State) AddItem(description string, quantity, price float64, taxType string) (Item, error) {
	taxRate := s.TaxRates[taxType]
	if _, ok := s.TaxRates[taxType]; !ok {
		taxRate = 16.0
	}
	if taxType == "exempt" {
		taxRate = 0.0
	}

	base, tax := s.CalculateItemTax(price, taxRate)

	item := Item{
		Description: description,
		Quantity:    quantity,
		Price:       price,
		TaxType:     taxType,
		TaxRate:     taxRate,
		Base:        base * quantity,
		Tax:         tax * quantity,
		Total:       (base + tax) * quantity,
	}

	s.CurrentItems = append(s.CurrentItems, item)
	s.SubtotalBases += item.Base
	s.SubtotalTax += item.Tax
	s.AmountPayable += item.Total

	block, ok := s.TaxTotals[taxType]
	if !ok {
		return Item{}, fmt.Errorf("'%s'", taxType)
	}
	block.Base += item.Base
	block.Tax += item.Tax
	s.TaxTotals[taxType] = block

	s.TotalSales += item.Total
	s.TotalTax += item.Tax
	s.DailySales += item.Total
	s.DailyTax += item.Tax

	return item, nil
}

func (s *State) AddPayment(amount float64, method string) {
	s.PaymentsMade += amount
	s.PaymentCount++
	s.AmountPayable -= amount
	s.PaymentTotals.Set(method, s.PaymentTotals.GetOr(method, 0.0)+amount)
	s.DocPayments.Set(method, s.DocPayments.GetOr(method, 0.0)+amount)
}

func (s *State) OpenDocument(docType string) {
	s.DocumentOpen = true
	s.DocumentType = docType
	s.CurrentItems = []Item{}
	s.SubtotalBases = 0.0
	s.SubtotalTax = 0.0
	s.AmountPayable = 0.0
	s.PaymentsMade = 0.0
	s.PaymentCount = 0
	s.DocPayments = orderedmap.New[string, float64]()
	s.SubtotalPrinted = false
	if docType != "non_fiscal" {
		s.CurrentState = "fiscal"
	} else {
		s.CurrentState = "non_fiscal"
	}
}

func (s *State) CloseDocument() *Document {
	if !s.DocumentOpen {
		return nil
	}

	doc := &Document{
		Type:          s.DocumentType,
		Number:        0,
		Items:         append([]Item{}, s.CurrentItems...),
		SubtotalBases: s.SubtotalBases,
		SubtotalTax:   s.SubtotalTax,
		Total:         s.SubtotalBases + s.SubtotalTax,
		Customer: Customer{
			Rif:     s.CustomerRif,
			Name:    s.CustomerName,
			Address: s.CustomerAddress,
		},
		Payments:        s.DocPayments.Clone(),
		Timestamp:       PyTime{time.Now()},
		SerialNumber:    s.SerialNumber,
		Rif:             s.Rif,
		Company:         s.Company,
		ReferenceDate:   s.ReferenceDate,
		ReferenceSerial: s.ReferenceSerial,
	}

	switch s.DocumentType {
	case "invoice":
		s.InvoiceCounter++
		s.FiscalCounter++
		s.DailyInvoices++
		doc.Number = s.InvoiceCounter
		now := PyTime{time.Now()}
		s.LastInvoiceDate = &now
	case "credit_note":
		s.CreditNoteCounter++
		s.FiscalCounter++
		s.DailyCreditNotes++
		doc.Number = s.CreditNoteCounter
		doc.ReferenceInvoice = s.ReferenceInvoice
	case "debit_note":
		s.DebitNoteCounter++
		s.FiscalCounter++
		s.DailyDebitNotes++
		doc.Number = s.DebitNoteCounter
		doc.ReferenceInvoice = s.ReferenceInvoice
	case "non_fiscal":
		s.NonFiscalCounter++
		s.DailyNonFiscal++
		doc.Number = s.NonFiscalCounter
	}

	doc.Paid = s.PaymentsMade
	if v := s.PaymentsMade - (s.SubtotalBases + s.SubtotalTax); v > 0 {
		doc.Change = v
	} else {
		doc.Change = 0
	}

	s.DocumentOpen = false
	s.DocumentType = ""
	s.CurrentState = "waiting"
	s.CurrentItems = []Item{}
	s.SubtotalBases = 0.0
	s.SubtotalTax = 0.0
	s.AmountPayable = 0.0
	s.PaymentsMade = 0.0
	s.PaymentCount = 0
	s.DocPayments = orderedmap.New[string, float64]()
	s.SubtotalPrinted = false
	s.CustomerRif = ""
	s.CustomerName = ""
	s.CustomerAddress = ""
	s.CustomerPhone = ""
	s.ReferenceInvoice = ""
	s.ReferenceDate = ""
	s.ReferenceSerial = ""

	payload, err := json.Marshal(doc)
	docSize := 0
	if err == nil {
		docSize = len(payload)
	}
	s.AuditMemoryUsed += float64(docSize) / 1024 / 1024
	s.AuditMemoryFree = s.AuditMemoryTotal - s.AuditMemoryUsed

	return doc
}

func (s *State) GenerateZReport() *Report {
	z := &Report{
		Type:             "Z",
		Number:           s.ZReportCounter + 1,
		Timestamp:        PyTime{time.Now()},
		LastInvoice:      s.InvoiceCounter,
		LastCreditNote:   s.CreditNoteCounter,
		LastDebitNote:    s.DebitNoteCounter,
		TotalSales:       s.DailySales,
		TotalTax:         s.DailyTax,
		TotalDiscounts:   s.DailyDiscounts,
		TotalSurcharges:  s.DailySurcharges,
		DailyInvoices:    s.DailyInvoices,
		DailyCreditNotes: s.DailyCreditNotes,
		DailyDebitNotes:  s.DailyDebitNotes,
		DailyNonFiscal:   s.DailyNonFiscal,
		LifetimeSales:    s.TotalSales,
		LifetimeTax:      s.TotalTax,
		TaxTotals:        copyBlockMap(s.TaxTotals),
		CreditNoteTotals: copyBlockMap(s.CreditNoteTotals),
		DebitNoteTotals:  copyBlockMap(s.DebitNoteTotals),
		Payments:         s.PaymentTotals.Clone(),
	}

	s.ZReportCounter++
	s.DailyClosureCounter++
	now := PyTime{time.Now()}
	s.LastZReportDate = &now
	s.ZReports = append(s.ZReports, z)

	s.DailySales = 0.0
	s.DailyTax = 0.0
	s.DailyDiscounts = 0.0
	s.DailySurcharges = 0.0
	s.DailyInvoices = 0
	s.DailyCreditNotes = 0
	s.DailyDebitNotes = 0
	s.DailyNonFiscal = 0
	s.TaxTotals = newTaxBlockMap()
	s.CreditNoteTotals = newTaxBlockMap()
	s.DebitNoteTotals = newTaxBlockMap()
	s.PaymentTotals = orderedmap.New[string, float64]()

	return z
}

func (s *State) GenerateXReport() *Report {
	x := &Report{
		Type:             "X",
		Number:           s.XReportCounter + 1,
		Timestamp:        PyTime{time.Now()},
		LastInvoice:      s.InvoiceCounter,
		LastCreditNote:   s.CreditNoteCounter,
		LastDebitNote:    s.DebitNoteCounter,
		TotalSales:       s.DailySales,
		TotalTax:         s.DailyTax,
		DailyInvoices:    s.DailyInvoices,
		DailyCreditNotes: s.DailyCreditNotes,
		DailyDebitNotes:  s.DailyDebitNotes,
		DailyNonFiscal:   s.DailyNonFiscal,
		TaxTotals:        copyBlockMap(s.TaxTotals),
		CreditNoteTotals: copyBlockMap(s.CreditNoteTotals),
		DebitNoteTotals:  copyBlockMap(s.DebitNoteTotals),
		Payments:         s.PaymentTotals.Clone(),
	}
	s.XReportCounter++
	s.XReports = append(s.XReports, x)
	return x
}

func copyBlockMap(m map[string]TaxBlock) map[string]TaxBlock {
	out := make(map[string]TaxBlock, len(m))
	for k, v := range m {
		out[k] = TaxBlock{Base: v.Base, Tax: v.Tax}
	}
	return out
}

type S1Data struct {
	MachineNumber   string
	Rif             string
	AuditCounter    int
	DailyClosure    int
	LastInvoice     int
	LastCreditNote  int
	LastDebitNote   int
	LastNonFiscal   int
	TotalSales      float64
	CurrentDateTime string
}

func (s *State) GetS1Data() S1Data {
	return S1Data{
		MachineNumber:   s.SerialNumber,
		Rif:             s.Rif,
		AuditCounter:    s.FiscalCounter,
		DailyClosure:    s.DailyClosureCounter,
		LastInvoice:     s.InvoiceCounter,
		LastCreditNote:  s.CreditNoteCounter,
		LastDebitNote:   s.DebitNoteCounter,
		LastNonFiscal:   s.NonFiscalCounter,
		TotalSales:      s.DailySales,
		CurrentDateTime: time.Now().Format("2006-01-02 15:04:05"),
	}
}

type S2Data struct {
	Condition        int
	TypeDocument     int
	QuantityArticles int
	SubtotalBases    float64
	SubtotalTax      float64
	AmountPayable    float64
	PaymentsMade     int
}

func (s *State) GetS2Data() S2Data {
	condition := 1
	if s.DocumentOpen {
		condition = 0
	}
	typeDoc := 0
	if s.DocumentType != "" {
		switch s.DocumentType {
		case "invoice":
			typeDoc = 0
		case "credit_note":
			typeDoc = 1
		case "debit_note":
			typeDoc = 2
		default:
			typeDoc = 0
		}
	}
	return S2Data{
		Condition:        condition,
		TypeDocument:     typeDoc,
		QuantityArticles: len(s.CurrentItems),
		SubtotalBases:    pyfmt.PyRound(s.SubtotalBases, 2),
		SubtotalTax:      pyfmt.PyRound(s.SubtotalTax, 2),
		AmountPayable:    pyfmt.PyRound(s.AmountPayable, 2),
		PaymentsMade:     s.PaymentCount,
	}
}

type S3Data struct {
	Tax1     float64
	Tax2     float64
	Tax3     float64
	TypeTax1 int
	TypeTax2 int
	TypeTax3 int
}

func (s *State) GetS3Data() S3Data {
	return S3Data{
		Tax1:     s.TaxRates["general"],
		Tax2:     s.TaxRates["reduced"],
		Tax3:     s.TaxRates["additional"],
		TypeTax1: s.TaxType,
		TypeTax2: s.TaxType,
		TypeTax3: s.TaxType,
	}
}

type S5Data struct {
	MachineNumber       string
	Rif                 string
	AuditMemoryNumber   int
	AuditMemoryTotal    float64
	AuditMemoryFree     float64
	RegisteredDocuments int
}

func (s *State) GetS5Data() S5Data {
	return S5Data{
		MachineNumber:       s.SerialNumber,
		Rif:                 s.Rif,
		AuditMemoryNumber:   s.AuditMemoryNumber,
		AuditMemoryTotal:    s.AuditMemoryTotal,
		AuditMemoryFree:     pyfmt.PyRound(s.AuditMemoryFree, 2),
		RegisteredDocuments: s.FiscalCounter,
	}
}
