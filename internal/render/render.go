package render

import (
	"fmt"
	"math"
	"strings"
	"time"

	"simuladorfiscal/internal/pyfmt"
	"simuladorfiscal/internal/state"
)

const PAPER_WIDTH = 42

var UNITS = []string{
	"", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE",
	"OCHO", "NUEVE", "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE",
	"QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE",
	"VEINTE", "VEINTIUNO", "VEINTIDÓS", "VEINTITRÉS", "VEINTICUATRO",
	"VEINTICINCO", "VEINTISÉIS", "VEINTISIETE", "VEINTIOCHO",
	"VEINTINUEVE",
}

var TENS = []string{"", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA",
	"SETENTA", "OCHENTA", "NOVENTA"}

var HUNDREDS = []string{"", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
	"QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"}

func numToWordsUpTo999(n int) string {
	if n == 0 {
		return ""
	}
	if n == 100 {
		return "CIEN"
	}
	h := n / 100
	rest := n % 100
	var parts []string
	if h != 0 {
		parts = append(parts, HUNDREDS[h])
	}
	if rest != 0 {
		if rest < 30 {
			parts = append(parts, UNITS[rest])
		} else {
			t := rest / 10
			u := rest % 10
			word := TENS[t]
			if u != 0 {
				word += " Y " + UNITS[u]
			}
			parts = append(parts, word)
		}
	}
	return strings.Join(parts, " ")
}

func NumberToWords(amount float64) string {
	whole := int(math.Abs(amount))
	cents := int(pyfmt.PyRound((math.Abs(amount)-float64(whole))*100, 0))

	var words string
	if whole == 0 {
		words = "CERO"
	} else {
		var chunks []string
		millions := whole / 1000000
		rest := whole % 1000000
		thousands := rest / 1000
		units := rest % 1000
		if millions != 0 {
			if millions == 1 {
				chunks = append(chunks, "UN MILLÓN")
			} else {
				chunks = append(chunks, numToWordsUpTo999(millions)+" MILLONES")
			}
		}
		if thousands != 0 {
			if thousands == 1 {
				chunks = append(chunks, "MIL")
			} else {
				chunks = append(chunks, numToWordsUpTo999(thousands)+" MIL")
			}
		}
		if units != 0 {
			chunks = append(chunks, numToWordsUpTo999(units))
		}
		words = strings.Join(chunks, " ")
	}

	return fmt.Sprintf("%s CON %02d/100", words, cents)
}

func center(text string) string {
	return pyfmt.Center(text, PAPER_WIDTH)
}

func rule(char string) string {
	return strings.Repeat(char, PAPER_WIDTH)
}

func kv(key, value, sep string) string {
	left := key + sep + " "
	pad := PAPER_WIDTH - pyfmt.Count(left) - pyfmt.Count(value)
	if pad < 1 {
		return pyfmt.Slice(left+value, 0, PAPER_WIDTH)
	}
	return left + strings.Repeat(" ", pad) + value
}

func money(value float64) string {
	return pyfmt.Money(value)
}

func wrap(text string, width int) []string {
	words := strings.Fields(text)
	var lines []string
	current := ""
	for _, w := range words {
		if current == "" {
			current = w
		} else if pyfmt.Count(current)+1+pyfmt.Count(w) <= width {
			current += " " + w
		} else {
			lines = append(lines, current)
			current = w
		}
	}
	if current != "" {
		lines = append(lines, current)
	}
	if len(lines) == 0 {
		return []string{""}
	}
	return lines
}

func companyBlock(c state.Company) []string {
	var lines []string
	name := c.RazonSocial
	if name == "" {
		name = "EMPRESA SIN NOMBRE"
	}
	lines = append(lines, center(strings.ToUpper(name)))
	if c.Rif != "" {
		lines = append(lines, center("RIF: "+c.Rif))
	}
	if c.LogoText != "" && c.LogoText != name {
		lines = append(lines, center(strings.ToUpper(c.LogoText)))
	}
	if c.Direccion != "" {
		for _, l := range wrap(c.Direccion, 40) {
			lines = append(lines, center(l))
		}
	}
	locality := joinNonEmpty([]string{c.Municipio, c.Ciudad, c.Estado}, " - ")
	if locality != "" {
		for _, l := range wrap(locality, 40) {
			lines = append(lines, center(l))
		}
	}
	if c.Telefono != "" {
		lines = append(lines, center("Telf: "+c.Telefono))
	}
	if c.RepresentanteLegal != "" {
		rep := "Rep. Legal: " + c.RepresentanteLegal
		if c.CedulaRepresentante != "" {
			rep += " - C.I. " + c.CedulaRepresentante
		}
		for _, l := range wrap(rep, 40) {
			lines = append(lines, center(l))
		}
	}
	if c.ActividadEconomica != "" {
		for _, l := range wrap("Actividad: "+c.ActividadEconomica, 40) {
			lines = append(lines, center(l))
		}
	}
	if c.ContribuyenteEspecial {
		lines = append(lines, center("CONTRIBUYENTE ESPECIAL"))
	}
	if c.AgenteRetencion {
		lines = append(lines, center("AGENTE DE RETENCION IVA"))
	}
	return lines
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

var docTitles = map[string]string{
	"invoice":     "FACTURA FISCAL",
	"credit_note": "NOTA DE CREDITO",
	"debit_note":  "NOTA DE DEBITO",
	"non_fiscal":  "DOCUMENTO NO FISCAL",
}

var taxLabels = map[string]string{
	"general":    "G16",
	"reduced":    "R8",
	"additional": "A30",
	"exempt":     "EX",
}

func paymentLabel(method string) string {
	labels := map[string]string{
		"cash": "EFECTIVO", "card": "TARJETA", "transfer": "TRANSFERENCIA",
		"mobile": "PAGO MOVIL", "credit": "CREDITO", "check": "CHEQUE",
		"pay_0": "EFECTIVO", "pay_1": "TARJETA", "pay_2": "TRANSFERENCIA",
	}
	if v, ok := labels[method]; ok {
		return v
	}
	return strings.ToUpper(method)
}

func RenderReceipt(doc *state.Document, company state.Company) []string {
	var lines []string

	lines = append(lines, companyBlock(company)...)
	lines = append(lines, rule("="))
	docType := doc.Type
	if docType == "" {
		docType = "invoice"
	}
	title, ok := docTitles[docType]
	if !ok {
		title = "DOCUMENTO FISCAL"
	}
	lines = append(lines, center(title))
	lines = append(lines, center(fmt.Sprintf("N° %08d", doc.Number)))
	ts := doc.Timestamp
	if !ts.IsZero() {
		lines = append(lines, center(ts.Format("02/01/2006  15:04:05")))
	}
	lines = append(lines, rule("="))

	cust := doc.Customer
	lines = append(lines, "CLIENTE:")
	if cust.Rif != "" {
		lines = append(lines, "  RIF/C.I: "+cust.Rif)
	}
	if cust.Name != "" {
		for _, l := range wrap("  "+cust.Name, 42) {
			lines = append(lines, l)
		}
	}
	if cust.Address != "" {
		for _, l := range wrap("  "+cust.Address, 42) {
			lines = append(lines, l)
		}
	}
	if cust.Rif == "" && cust.Name == "" && cust.Address == "" {
		lines = append(lines, "  CONSUMIDOR FINAL")
	}
	lines = append(lines, rule("-"))

	if docType == "credit_note" || docType == "debit_note" {
		if doc.ReferenceInvoice != "" {
			lines = append(lines, kv("FACT. REFERIDA", doc.ReferenceInvoice, ":"))
		}
		if doc.ReferenceDate != "" {
			lines = append(lines, kv("FECHA ORIG.", doc.ReferenceDate, ":"))
		}
		if doc.ReferenceSerial != "" {
			lines = append(lines, kv("SERIE ORIG.", doc.ReferenceSerial, ":"))
		}
		lines = append(lines, rule("-"))
	}

	lines = append(lines, fmt.Sprintf("%7s %-17s %7s %4s %9s",
		"CANT", "DESCRIPCION", "PREC", "IVA", "IMPORTE"))
	lines = append(lines, rule("-"))
	for _, item := range doc.Items {
		desc := pyfmt.Slice(item.Description, 0, 17)
		taxLabel := taxLabels[item.TaxType]
		if taxLabel == "" {
			taxLabel = "G16"
		}
		lines = append(lines, fmt.Sprintf("%7s %-17s %7s %4s %9s",
			pyfmt.Fixed(item.Quantity, 7, 3), desc,
			pyfmt.Fixed(item.Price, 7, 2), taxLabel,
			pyfmt.Fixed(item.Total, 9, 2)))
		if pyfmt.Count(item.Description) > 17 {
			for _, l := range wrap("   "+item.Description, 42)[1:] {
				lines = append(lines, l)
			}
		}
	}
	lines = append(lines, rule("-"))

	lines = append(lines, kv("SUBTOTAL", money(doc.SubtotalBases+doc.SubtotalTax), ":"))
	byRate := map[string]*state.TaxBlock{}
	for i := range doc.Items {
		rate := doc.Items[i].TaxType
		if _, ok := byRate[rate]; !ok {
			byRate[rate] = &state.TaxBlock{}
		}
		byRate[rate].Base += doc.Items[i].Base
		byRate[rate].Tax += doc.Items[i].Tax
	}
	pcts := map[string]string{
		"general": "16%", "reduced": "8%", "additional": "30%", "exempt": "EXENTO",
	}
	for _, rate := range []string{"general", "reduced", "additional", "exempt"} {
		block, ok := byRate[rate]
		if !ok {
			continue
		}
		pct := pcts[rate]
		if rate != "exempt" {
			lines = append(lines, kv("  BASE IVA "+pct, money(block.Base), ":"))
			lines = append(lines, kv("  IVA "+pct, money(block.Tax), ":"))
		} else {
			lines = append(lines, kv("  BASE EXENTA", money(block.Base), ":"))
		}
	}
	lines = append(lines, rule("="))
	lines = append(lines, kv("TOTAL Bs.", money(doc.Total), ":"))
	lines = append(lines, rule("="))

	if doc.Payments != nil {
		for _, method := range doc.Payments.Keys() {
			amount, _ := doc.Payments.Get(method)
			lines = append(lines, kv(paymentLabel(method), money(amount), ":"))
		}
	}
	if doc.Change != 0 {
		lines = append(lines, kv("CAMBIO", money(doc.Change), ":"))
	}

	lines = append(lines, rule("-"))
	words := NumberToWords(doc.Total)
	for _, w := range wrap("SON: "+words, 42) {
		lines = append(lines, "  "+w)
	}

	lines = append(lines, rule("-"))
	if doc.SerialNumber != "" {
		lines = append(lines, kv("MAQUINA", doc.SerialNumber, ":"))
	}
	if doc.Rif != "" {
		lines = append(lines, kv("RIF MAQ.", doc.Rif, ":"))
	}
	if company.CondicionesPago != "" {
		lines = append(lines, kv("COND. PAGO", company.CondicionesPago, ":"))
	}
	lines = append(lines, center("ART. 63 Ley IVA - Ley Org."))
	lines = append(lines, center("Simplificacion y Racionalizacion"))
	lines = append(lines, center("del Proceso Tributario"))
	lines = append(lines, rule("-"))
	lines = append(lines, center("GRACIAS POR SU COMPRA"))
	lines = append(lines, center("* * * * * * * * * * * * * * * *"))
	lines = append(lines, center("DOCUMENTO FISCAL DIGITAL"))
	lines = append(lines, center("SIMULADOR - NO VALOR FISCAL"))
	return lines
}

func reportCommonLines(rep *state.Report, company state.Company, title string) []string {
	var lines []string
	lines = append(lines, companyBlock(company)...)
	lines = append(lines, rule("="))
	lines = append(lines, center(title))
	lines = append(lines, center(fmt.Sprintf("REPORTE N° %04d", rep.Number)))
	ts := rep.Timestamp
	if !ts.IsZero() {
		lines = append(lines, center(ts.Format("02/01/2006  15:04:05")))
	}
	lines = append(lines, rule("="))
	return lines
}

func reportBodyLines(rep *state.Report) []string {
	var lines []string
	lines = append(lines, "DOCUMENTOS DEL DIA:")
	lines = append(lines, kv("  Facturas", fmt.Sprintf("%d", rep.DailyInvoices), ":"))
	lines = append(lines, kv("  Notas de credito", fmt.Sprintf("%d", rep.DailyCreditNotes), ":"))
	lines = append(lines, kv("  Notas de debito", fmt.Sprintf("%d", rep.DailyDebitNotes), ":"))
	lines = append(lines, kv("  No fiscales", fmt.Sprintf("%d", rep.DailyNonFiscal), ":"))
	lines = append(lines, rule("-"))

	lines = append(lines, "VENTAS POR ALICUOTA:")
	labels := map[string]string{
		"general": "GENERAL 16%", "reduced": "REDUCIDA 8%",
		"additional": "ADICIONAL 30%", "exempt": "EXENTO",
	}
	for _, rate := range []string{"general", "reduced", "additional", "exempt"} {
		block, ok := rep.TaxTotals[rate]
		if !ok {
			block = state.TaxBlock{}
		}
		if block.Base != 0 || block.Tax != 0 {
			lines = append(lines, kv("  "+labels[rate], money(block.Base), ":"))
			if rate != "exempt" {
				lines = append(lines, kv("    IVA", money(block.Tax), ":"))
			}
		}
	}
	lines = append(lines, rule("-"))

	lines = append(lines, "FORMAS DE PAGO:")
	if rep.Payments != nil && rep.Payments.Len() > 0 {
		for _, method := range rep.Payments.Keys() {
			amount, _ := rep.Payments.Get(method)
			low := strings.ToLower(method)
			labels := map[string]string{
				"cash": "EFECTIVO", "card": "TARJETA", "transfer": "TRANSFERENCIA",
				"mobile": "PAGO MOVIL", "credit": "CREDITO", "check": "CHEQUE",
				"pay_0": "EFECTIVO", "pay_1": "TARJETA", "pay_2": "TRANSFERENCIA",
			}
			label, ok := labels[low]
			if !ok {
				label = strings.ToUpper(method)
			}
			lines = append(lines, kv("  "+label, money(amount), ":"))
		}
	} else {
		lines = append(lines, "  (sin pagos registrados)")
	}
	lines = append(lines, rule("="))

	lines = append(lines, kv("TOTAL VENTAS", money(rep.TotalSales), ":"))
	lines = append(lines, kv("TOTAL IVA", money(rep.TotalTax), ":"))
	if rep.TotalDiscounts != 0 {
		lines = append(lines, kv("DESCUENTOS", money(rep.TotalDiscounts), ":"))
	}
	if rep.TotalSurcharges != 0 {
		lines = append(lines, kv("RECARGOS", money(rep.TotalSurcharges), ":"))
	}
	lines = append(lines, rule("="))
	return lines
}

func RenderXReport(rep *state.Report, company state.Company) []string {
	lines := reportCommonLines(rep, company, "REPORTE X - CORTE DE CAJA")
	lines = append(lines, reportBodyLines(rep)...)
	lines = append(lines, center("ESTE REPORTE NO REINICIA"))
	lines = append(lines, center("LOS TOTALES DEL DIA"))
	lines = append(lines, rule("-"))
	if rep.LastInvoice != 0 {
		lines = append(lines, kv("ULTIMA FACTURA", fmt.Sprintf("%08d", rep.LastInvoice), ":"))
	}
	lines = append(lines, center("* * * * * * * * * * * * * * * *"))
	lines = append(lines, center("SIMULADOR - NO VALOR FISCAL"))
	return lines
}

func RenderZReport(rep *state.Report, company state.Company) []string {
	lines := reportCommonLines(rep, company, "REPORTE Z - CIERRE DIARIO")
	lines = append(lines, reportBodyLines(rep)...)
	lines = append(lines, center("CIERRE DEL DIA"))
	lines = append(lines, center("TOTALES REINICIADOS TRAS"))
	lines = append(lines, center("ESTE REPORTE"))
	lines = append(lines, rule("-"))
	if rep.LastInvoice != 0 {
		lines = append(lines, kv("ULTIMA FACTURA", fmt.Sprintf("%08d", rep.LastInvoice), ":"))
	}
	lines = append(lines, kv("CIERRES DIARIOS", fmt.Sprintf("%d", rep.Number), ":"))
	lines = append(lines, center("* * * * * * * * * * * * * * * *"))
	lines = append(lines, center("SIMULADOR - NO VALOR FISCAL"))
	return lines
}

func RenderOpenDocument(s *state.State) []string {
	if !s.DocumentOpen {
		return []string{}
	}
	docType := s.DocumentType
	if docType == "" {
		docType = "invoice"
	}
	number := s.InvoiceCounter + 1
	switch docType {
	case "credit_note":
		number = s.CreditNoteCounter + 1
	case "debit_note":
		number = s.DebitNoteCounter + 1
	case "non_fiscal":
		number = s.NonFiscalCounter + 1
	}
	change := s.PaymentsMade - (s.SubtotalBases + s.SubtotalTax)
	if change < 0 {
		change = 0
	}
	doc := &state.Document{
		Type:          docType,
		Number:        number,
		Items:         append([]state.Item{}, s.CurrentItems...),
		SubtotalBases: s.SubtotalBases,
		SubtotalTax:   s.SubtotalTax,
		Total:         s.SubtotalBases + s.SubtotalTax,
		Customer: state.Customer{
			Rif:     s.CustomerRif,
			Name:    s.CustomerName,
			Address: s.CustomerAddress,
		},
		Payments:     s.DocPayments.Clone(),
		Timestamp:    state.PyTime{Time: time.Now()},
		SerialNumber: s.SerialNumber,
		Rif:          s.Rif,
		Company:      s.Company,
	}
	lines := RenderReceipt(doc, s.Company)
	out := []string{pyfmt.LJust("", PAPER_WIDTH)}
	out = append(out, pyfmt.Center("* DOCUMENTO EN CURSO - VISTA PREVIA *", PAPER_WIDTH))
	out = append(out, lines...)
	return out
}

func RenderNonFiscal(doc *state.Document, company state.Company) []string {
	var lines []string
	lines = append(lines, companyBlock(company)...)
	lines = append(lines, rule("="))
	lines = append(lines, center("DOCUMENTO NO FISCAL"))
	lines = append(lines, center(fmt.Sprintf("N° %08d", doc.Number)))
	ts := doc.Timestamp
	if !ts.IsZero() {
		lines = append(lines, center(ts.Format("02/01/2006  15:04:05")))
	}
	lines = append(lines, rule("="))
	for _, item := range doc.Items {
		for _, l := range wrap(item.Description, 42) {
			lines = append(lines, l)
		}
	}
	lines = append(lines, rule("-"))
	lines = append(lines, center("DOCUMENTO SIN VALOR FISCAL"))
	return lines
}
