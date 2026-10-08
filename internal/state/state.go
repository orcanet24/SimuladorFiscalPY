package state

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"simuladorfiscal/internal/orderedmap"
	"simuladorfiscal/internal/pyfmt"
)

type PyTime struct {
	time.Time
}

func (t PyTime) MarshalJSON() ([]byte, error) {
	return json.Marshal(t.Format("2006-01-02T15:04:05.999999"))
}

func (t *PyTime) UnmarshalJSON(b []byte) error {
	var s string
	if err := json.Unmarshal(b, &s); err != nil {
		return err
	}
	if s == "" {
		t.Time = time.Time{}
		return nil
	}
	for _, layout := range []string{
		"2006-01-02T15:04:05.999999999",
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05.999999999",
		"2006-01-02 15:04:05",
	} {
		if tt, err := time.Parse(layout, s); err == nil {
			t.Time = tt
			return nil
		}
	}
	return fmt.Errorf("invalid timestamp %q", s)
}

type TaxBlock struct {
	Base float64 `json:"base"`
	Tax  float64 `json:"tax"`
}

type Item struct {
	Description string  `json:"description"`
	Quantity    float64 `json:"quantity"`
	Price       float64 `json:"price"`
	TaxType     string  `json:"tax_type"`
	TaxRate     float64 `json:"tax_rate"`
	Base        float64 `json:"base"`
	Tax         float64 `json:"tax"`
	Total       float64 `json:"total"`
}

type Customer struct {
	Rif     string `json:"rif"`
	Name    string `json:"name"`
	Address string `json:"address"`
}

type Company struct {
	Rif                   string `json:"rif"`
	RazonSocial           string `json:"razon_social"`
	Direccion             string `json:"direccion"`
	Municipio             string `json:"municipio"`
	Ciudad                string `json:"ciudad"`
	Estado                string `json:"estado"`
	Telefono              string `json:"telefono"`
	Email                 string `json:"email"`
	RepresentanteLegal    string `json:"representante_legal"`
	CedulaRepresentante   string `json:"cedula_representante"`
	ActividadEconomica    string `json:"actividad_economica"`
	Nif                   string `json:"nif"`
	Moneda                string `json:"moneda"`
	LogoText              string `json:"logo_text"`
	CondicionesPago       string `json:"condiciones_pago"`
	ContribuyenteEspecial bool   `json:"contribuyente_especial"`
	AgenteRetencion       bool   `json:"agente_retencion"`
}

func (c *Company) Set(key string, value any) {
	switch key {
	case "rif":
		if v, ok := value.(string); ok {
			c.Rif = v
		}
	case "razon_social":
		if v, ok := value.(string); ok {
			c.RazonSocial = v
		}
	case "direccion":
		if v, ok := value.(string); ok {
			c.Direccion = v
		}
	case "municipio":
		if v, ok := value.(string); ok {
			c.Municipio = v
		}
	case "ciudad":
		if v, ok := value.(string); ok {
			c.Ciudad = v
		}
	case "estado":
		if v, ok := value.(string); ok {
			c.Estado = v
		}
	case "telefono":
		if v, ok := value.(string); ok {
			c.Telefono = v
		}
	case "email":
		if v, ok := value.(string); ok {
			c.Email = v
		}
	case "representante_legal":
		if v, ok := value.(string); ok {
			c.RepresentanteLegal = v
		}
	case "cedula_representante":
		if v, ok := value.(string); ok {
			c.CedulaRepresentante = v
		}
	case "actividad_economica":
		if v, ok := value.(string); ok {
			c.ActividadEconomica = v
		}
	case "nif":
		if v, ok := value.(string); ok {
			c.Nif = v
		}
	case "moneda":
		if v, ok := value.(string); ok {
			c.Moneda = v
		}
	case "logo_text":
		if v, ok := value.(string); ok {
			c.LogoText = v
		}
	case "condiciones_pago":
		if v, ok := value.(string); ok {
			c.CondicionesPago = v
		}
	case "contribuyente_especial":
		if v, ok := value.(bool); ok {
			c.ContribuyenteEspecial = v
		}
	case "agente_retencion":
		if v, ok := value.(bool); ok {
			c.AgenteRetencion = v
		}
	}
}

func NewCompany() Company {
	return Company{
		Moneda:          "Bs.",
		CondicionesPago: "CONTADO",
	}
}

type HistoryEntry struct {
	Seq      int    `json:"seq"`
	TS       string `json:"ts"`
	Command  string `json:"command"`
	Response string `json:"response"`
	OK       bool   `json:"ok"`
}

type PrintJob struct {
	ID    int            `json:"id"`
	Kind  string         `json:"kind"`
	Title string         `json:"title"`
	TS    string         `json:"ts"`
	Brand string         `json:"brand"`
	Lines []string       `json:"lines"`
	Meta  map[string]any `json:"meta"`
}

type Report struct {
	Type             string                           `json:"type"`
	Number           int                              `json:"number"`
	Timestamp        PyTime                           `json:"timestamp"`
	LastInvoice      int                              `json:"last_invoice"`
	LastCreditNote   int                              `json:"last_credit_note"`
	LastDebitNote    int                              `json:"last_debit_note"`
	TotalSales       float64                          `json:"total_sales"`
	TotalTax         float64                          `json:"total_tax"`
	TotalDiscounts   float64                          `json:"total_discounts"`
	TotalSurcharges  float64                          `json:"total_surcharges"`
	DailyInvoices    int                              `json:"daily_invoices"`
	DailyCreditNotes int                              `json:"daily_credit_notes"`
	DailyDebitNotes  int                              `json:"daily_debit_notes"`
	DailyNonFiscal   int                              `json:"daily_non_fiscal"`
	LifetimeSales    float64                          `json:"lifetime_sales"`
	LifetimeTax      float64                          `json:"lifetime_tax"`
	TaxTotals        map[string]TaxBlock              `json:"tax_totals"`
	CreditNoteTotals map[string]TaxBlock              `json:"credit_note_totals"`
	DebitNoteTotals  map[string]TaxBlock              `json:"debit_note_totals"`
	Payments         *orderedmap.Map[string, float64] `json:"payments"`
}

type Document struct {
	Type             string                           `json:"type"`
	Number           int                              `json:"number"`
	Items            []Item                           `json:"items"`
	SubtotalBases    float64                          `json:"subtotal_bases"`
	SubtotalTax      float64                          `json:"subtotal_tax"`
	Total            float64                          `json:"total"`
	Customer         Customer                         `json:"customer"`
	Payments         *orderedmap.Map[string, float64] `json:"payments"`
	Timestamp        PyTime                           `json:"timestamp"`
	ReferenceInvoice string                           `json:"reference_invoice,omitempty"`
	Paid             float64                          `json:"paid"`
	Change           float64                          `json:"change"`
	SerialNumber     string                           `json:"serial_number"`
	Rif              string                           `json:"rif"`
	Company          Company                          `json:"company"`
	ReferenceDate    string                           `json:"reference_date"`
	ReferenceSerial  string                           `json:"reference_serial"`
}

type State struct {
	SerialNumber        string                           `json:"serial_number"`
	FiscalRegistration  string                           `json:"fiscal_registration"`
	Rif                 string                           `json:"rif"`
	Mode                string                           `json:"mode"`
	MemoryStatus        string                           `json:"memory_status"`
	CurrentState        string                           `json:"current_state"`
	FiscalCounter       int                              `json:"fiscal_counter"`
	InvoiceCounter      int                              `json:"invoice_counter"`
	CreditNoteCounter   int                              `json:"credit_note_counter"`
	DebitNoteCounter    int                              `json:"debit_note_counter"`
	NonFiscalCounter    int                              `json:"non_fiscal_counter"`
	ZReportCounter      int                              `json:"z_report_counter"`
	XReportCounter      int                              `json:"x_report_counter"`
	DailyClosureCounter int                              `json:"daily_closure_counter"`
	TotalSales          float64                          `json:"total_sales"`
	TotalTax            float64                          `json:"total_tax"`
	TotalDiscounts      float64                          `json:"total_discounts"`
	TotalSurcharges     float64                          `json:"total_surcharges"`
	DailySales          float64                          `json:"daily_sales"`
	DailyTax            float64                          `json:"daily_tax"`
	DailyDiscounts      float64                          `json:"daily_discounts"`
	DailySurcharges     float64                          `json:"daily_surcharges"`
	DailyInvoices       int                              `json:"daily_invoices"`
	DailyCreditNotes    int                              `json:"daily_credit_notes"`
	DailyDebitNotes     int                              `json:"daily_debit_notes"`
	DailyNonFiscal      int                              `json:"daily_non_fiscal"`
	TaxTotals           map[string]TaxBlock              `json:"tax_totals"`
	CreditNoteTotals    map[string]TaxBlock              `json:"credit_note_totals"`
	DebitNoteTotals     map[string]TaxBlock              `json:"debit_note_totals"`
	PaymentTotals       *orderedmap.Map[string, float64] `json:"payment_totals"`
	Company             Company                          `json:"company"`
	Headers             []string                         `json:"headers"`
	Footers             map[string]string                `json:"footers"`
	Flags               map[string]bool                  `json:"flags"`
	DocumentOpen        bool                             `json:"document_open"`
	DocumentType        string                           `json:"document_type"`
	CurrentItems        []Item                           `json:"current_items"`
	SubtotalBases       float64                          `json:"subtotal_bases"`
	SubtotalTax         float64                          `json:"subtotal_tax"`
	AmountPayable       float64                          `json:"amount_payable"`
	PaymentsMade        float64                          `json:"payments_made"`
	PaymentCount        int                              `json:"payment_count"`
	DocPayments         *orderedmap.Map[string, float64] `json:"doc_payments"`
	SubtotalPrinted     bool                             `json:"subtotal_printed"`
	CustomerRif         string                           `json:"customer_rif"`
	CustomerName        string                           `json:"customer_name"`
	CustomerAddress     string                           `json:"customer_address"`
	CustomerPhone       string                           `json:"customer_phone"`
	ReferenceInvoice    string                           `json:"reference_invoice"`
	ReferenceDate       string                           `json:"reference_date"`
	ReferenceSerial     string                           `json:"reference_serial"`
	AuditMemoryNumber   int                              `json:"audit_memory_number"`
	AuditMemoryTotal    float64                          `json:"audit_memory_total"`
	AuditMemoryFree     float64                          `json:"audit_memory_free"`
	AuditMemoryUsed     float64                          `json:"audit_memory_used"`
	ZReports            []*Report                        `json:"z_reports"`
	XReports            []*Report                        `json:"x_reports"`
	PrintJobs           []*PrintJob                      `json:"print_jobs"`
	PrintJobSeq         int                              `json:"print_job_seq"`
	TaxRates            map[string]float64               `json:"tax_rates"`
	TaxType             int                              `json:"tax_type"`
	LastInvoiceDate     *PyTime                          `json:"last_invoice_date"`
	LastZReportDate     *PyTime                          `json:"last_z_report_date"`

	Brand string `json:"-"`
	Model string `json:"-"`

	CustomerNameLine2 string `json:"-"`

	HasPaper  bool `json:"-"`
	PaperJam  bool `json:"-"`
	CoverOpen bool `json:"-"`
}

func takePrefix(s string, n int) string {
	r := []rune(s)
	if len(r) > n {
		return string(r[:n])
	}
	return s
}

func newTaxBlockMap() map[string]TaxBlock {
	return map[string]TaxBlock{
		"general":    {0, 0},
		"reduced":    {0, 0},
		"additional": {0, 0},
		"exempt":     {0, 0},
	}
}

func NewState(brand, model string) *State {
	s := &State{}
	s.Brand = strings.ToUpper(brand)
	s.Model = strings.ToUpper(model)
	s.SerialNumber = "ML" + strings.ToUpper(takePrefix(brand, 2)) + strings.ToUpper(takePrefix(model, 3)) + fmt.Sprintf("%05d", 10000)
	s.FiscalRegistration = "J-12345678-9"
	s.Rif = "J-12345678-9"
	s.Mode = "fiscal"
	s.MemoryStatus = "ok"
	s.CurrentState = "waiting"
	s.TaxTotals = newTaxBlockMap()
	s.CreditNoteTotals = newTaxBlockMap()
	s.DebitNoteTotals = newTaxBlockMap()
	s.PaymentTotals = orderedmap.New[string, float64]()
	s.DocPayments = orderedmap.New[string, float64]()
	s.TaxRates = map[string]float64{"general": 16.0, "reduced": 8.0, "additional": 30.0}
	s.TaxType = 1
	s.CurrentItems = []Item{}
	s.Company = NewCompany()
	s.AuditMemoryNumber = 1
	s.AuditMemoryTotal = 4.0
	s.AuditMemoryFree = 3.5
	s.AuditMemoryUsed = 0.5
	s.HasPaper = true
	s.CoverOpen = false
	s.Flags = map[string]bool{
		"print_logo":           false,
		"reduce_z_report":      false,
		"print_z_report_items": false,
		"print_customer_data":  false,
		"dont_open_drawer":     false,
		"paper_sensor_enabled": true,
	}
	s.Headers = []string{
		"RIF: J-12345678-9",
		"FACTURA FISCAL",
		"AVENIDA PRINCIPAL",
		"CARACAS - VENEZUELA",
		"", "", "", "",
	}
	s.Footers = map[string]string{
		"footer1": "GRACIAS POR SU COMPRA",
		"footer2": "", "footer3": "", "footer4": "",
		"footer5": "", "footer6": "", "footer7": "", "footer8": "",
	}
	s.ZReports = []*Report{}
	s.XReports = []*Report{}
	s.PrintJobs = []*PrintJob{}
	return s
}

func (s *State) GetStatusCode() byte {
	if s.Mode == "fiscal" {
		switch s.CurrentState {
		case "waiting":
			if s.MemoryStatus == "ok" {
				return 0x04
			} else if s.MemoryStatus == "almost_full" {
				return 0x07
			}
			return 0x0A
		case "fiscal":
			if s.MemoryStatus == "ok" {
				return 0x05
			} else if s.MemoryStatus == "almost_full" {
				return 0x08
			}
			return 0x0B
		case "non_fiscal":
			if s.MemoryStatus == "ok" {
				return 0x06
			} else if s.MemoryStatus == "almost_full" {
				return 0x09
			}
			return 0x0C
		}
	}
	return 0x04
}

func (s *State) GetErrorCode() byte {
	if !s.HasPaper {
		return 0x01
	}
	if s.PaperJam {
		return 0x02
	}
	if s.AuditMemoryFree <= 0.01 {
		return 0x6C
	}
	return 0x00
}

func (s *State) ProgramCompany(data map[string]any) Company {
	for key, value := range data {
		s.Company.Set(key, value)
	}
	if s.Company.Rif != "" {
		s.Rif = s.Company.Rif
		s.FiscalRegistration = s.Company.Rif
	}
	c := s.Company
	logo := c.LogoText
	if logo == "" {
		logo = c.RazonSocial
	}
	locality := joinNonEmpty([]string{c.Municipio, c.Estado}, " - ")
	headers := make([]string, 8)
	headers[0] = pyfmt.Slice(logo, 0, 40)
	headers[1] = pyfmt.Slice("RIF: "+c.Rif, 0, 40)
	headers[2] = pyfmt.Slice(c.Direccion, 0, 40)
	headers[3] = pyfmt.Slice(locality, 0, 40)
	if c.Telefono != "" {
		headers[4] = pyfmt.Slice("TEL: "+c.Telefono, 0, 40)
	} else {
		headers[4] = ""
	}
	if c.RepresentanteLegal != "" {
		headers[5] = pyfmt.Slice("REP. LEGAL: "+c.RepresentanteLegal, 0, 40)
	} else {
		headers[5] = ""
	}
	headers[6] = ""
	headers[7] = ""
	s.Headers = headers
	return c
}

func joinNonEmpty(parts []string, sep string) string {
	var kept []string
	for _, p := range parts {
		if p != "" {
			kept = append(kept, p)
		}
	}
	return strings.Join(kept, sep)
}
