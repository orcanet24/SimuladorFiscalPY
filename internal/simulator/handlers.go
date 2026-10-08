package simulator

import (
	"fmt"
	"strings"

	"simuladorfiscal/internal/pyfmt"
)

func (s *Simulator) handleTFHKA(cmdType string, params []any, raw string) (string, error) {
	st := s.State

	switch cmdType {
	case "ITEM", "ITEM_CREDIT", "ITEM_DEBIT":
		return s.handleItem(raw, cmdType, params)

	case "SUBTOTAL_PRINT":
		st.SubtotalPrinted = true
		return fmt.Sprintf("0|Subtotal: %s + %s = %s",
			pyfmt.F2(st.SubtotalBases), pyfmt.F2(st.SubtotalTax),
			pyfmt.F2(st.SubtotalBases+st.SubtotalTax)), nil

	case "SUBTOTAL_SILENT":
		return "0|OK", nil

	case "CLOSE_TOTALIZE":
		if st.DocumentOpen {
			doc := st.CloseDocument()
			if doc != nil {
				job := s.recordReceipt(doc)
				docTypeNames := map[string]string{
					"invoice":     "Factura",
					"credit_note": "Nota de Credito",
					"debit_note":  "Nota de Debito",
					"non_fiscal":  "Doc No Fiscal",
				}
				name, ok := docTypeNames[doc.Type]
				if !ok {
					name = "Documento"
				}
				return fmt.Sprintf("0|%s %d|Total: %s|Impreso:%d",
					name, doc.Number, pyfmt.F2(doc.Total), job.ID), nil
			}
		}
		return "0|Cerrado", nil

	case "OPEN_DRAWER":
		return "0|Gaveta abierta", nil

	case "OPEN_NON_FISCAL":
		st.OpenDocument("non_fiscal")
		return "0|DNF abierto", nil

	case "PRINT_NON_FISCAL_TEXT":
		return "0|Texto impreso", nil

	case "PRINT_NON_FISCAL_CONTENT":
		return "0|Contenido impreso", nil

	case "CLOSE_NON_FISCAL":
		if st.DocumentOpen {
			doc := st.CloseDocument()
			if doc != nil {
				s.recordReceipt(doc)
			}
		}
		return "0|DNF cerrado", nil

	case "COMMENT":
		return "0|Comentario", nil

	case "PAYMENT":
		var amount float64
		if len(params) > 0 {
			v, err := pyfmt.Float(params[0].(string))
			if err != nil {
				return "", err
			}
			amount = v
		}
		st.AddPayment(amount, "cash")
		return fmt.Sprintf("0|Pago: %s|Pendiente: %s",
			pyfmt.F2(amount), pyfmt.F2(st.AmountPayable)), nil

	case "PAYMENT_DESC":
		return "0|Descripcion pago", nil

	case "DISCOUNT":
		var amount float64
		if len(params) > 0 {
			v, err := pyfmt.Float(params[0].(string))
			if err != nil {
				return "", err
			}
			amount = v
		}
		st.TotalDiscounts += amount
		st.AmountPayable -= amount
		return fmt.Sprintf("0|Descuento: %s", pyfmt.F2(amount)), nil

	case "SURCHARGE":
		var amount float64
		if len(params) > 0 {
			v, err := pyfmt.Float(params[0].(string))
			if err != nil {
				return "", err
			}
			amount = v
		}
		st.TotalSurcharges += amount
		st.AmountPayable += amount
		return fmt.Sprintf("0|Recargo: %s", pyfmt.F2(amount)), nil

	case "CUSTOMER_RIF":
		st.CustomerRif = paramString(params)
		st.CustomerRif = strings.ReplaceAll(st.CustomerRif, "*", "")
		st.CustomerRif = strings.TrimSpace(st.CustomerRif)
		return "0|RIF registrado", nil

	case "CUSTOMER_NAME":
		st.CustomerName = paramString(params)
		st.CustomerName = strings.ReplaceAll(st.CustomerName, "*", "")
		st.CustomerName = strings.TrimSpace(st.CustomerName)
		return "0|Nombre registrado", nil

	case "CUSTOMER_ADDRESS":
		st.CustomerAddress = paramString(params)
		return "0|Direccion registrada", nil

	case "CUSTOMER_PHONE":
		st.CustomerPhone = paramString(params)
		return "0|Telefono registrado", nil

	case "INVOICE_NUMBER":
		st.ReferenceInvoice = paramString(params)
		st.ReferenceInvoice = strings.ReplaceAll(st.ReferenceInvoice, "*", "")
		st.ReferenceInvoice = strings.TrimSpace(st.ReferenceInvoice)
		return "0|Nro factura referenciada", nil

	case "INVOICE_DATE":
		st.ReferenceDate = paramString(params)
		st.ReferenceDate = strings.ReplaceAll(st.ReferenceDate, "*", "")
		st.ReferenceDate = strings.TrimSpace(st.ReferenceDate)
		return "0|Fecha factura referenciada", nil

	case "FISCAL_SERIAL":
		st.ReferenceSerial = paramString(params)
		st.ReferenceSerial = strings.ReplaceAll(st.ReferenceSerial, "*", "")
		st.ReferenceSerial = strings.TrimSpace(st.ReferenceSerial)
		return "0|Serial fiscal registrado", nil

	case "OPEN_CREDIT_NOTE":
		st.OpenDocument("credit_note")
		return "0|Nota credito abierta", nil

	case "OPEN_DEBIT_NOTE":
		st.OpenDocument("debit_note")
		return "0|Nota debito abierta", nil

	case "S1":
		s1 := st.GetS1Data()
		return fmt.Sprintf("0|%s|%s|%d|%d|%d|%d|%d|%d|%s|%s",
			s1.MachineNumber, s1.Rif, s1.AuditCounter, s1.DailyClosure,
			s1.LastInvoice, s1.LastCreditNote, s1.LastDebitNote, s1.LastNonFiscal,
			pyfmt.F2(s1.TotalSales), s1.CurrentDateTime), nil

	case "S2":
		s2 := st.GetS2Data()
		return fmt.Sprintf("%d|%d|%d|%s|%s|%s|%d",
			s2.Condition, s2.TypeDocument, s2.QuantityArticles,
			pyfmt.F2(s2.SubtotalBases), pyfmt.F2(s2.SubtotalTax),
			pyfmt.F2(s2.AmountPayable), s2.PaymentsMade), nil

	case "S3":
		s3 := st.GetS3Data()
		return fmt.Sprintf("%s|%s|%s|%d|%d|%d",
			pyfmt.F2(s3.Tax1), pyfmt.F2(s3.Tax2), pyfmt.F2(s3.Tax3),
			s3.TypeTax1, s3.TypeTax2, s3.TypeTax3), nil

	case "S4":
		var parts []string
		for _, method := range st.PaymentTotals.Keys() {
			v, _ := st.PaymentTotals.Get(method)
			parts = append(parts, pyfmt.F2(v))
		}
		return "0|" + strings.Join(parts, "|") + "|0.00", nil

	case "S5":
		s5 := st.GetS5Data()
		return fmt.Sprintf("%s|%s|%d|%s|%s|%d",
			s5.MachineNumber, s5.Rif, s5.AuditMemoryNumber,
			pyfmt.F2(s5.AuditMemoryTotal), pyfmt.F2(s5.AuditMemoryFree),
			s5.RegisteredDocuments), nil

	case "S8E":
		return strings.Join(st.Headers, "|"), nil

	case "S8P":
		var footers []string
		for i := 1; i <= 8; i++ {
			footers = append(footers, st.Footers[fmt.Sprintf("footer%d", i)])
		}
		return strings.Join(footers, "|"), nil

	case "U0X", "REPORT_X":
		x := st.GenerateXReport()
		job := s.recordReport(x, "X")
		return fmt.Sprintf("0|Reporte X #%d|Ventas: %s|IVA: %s|Impreso:%d",
			x.Number, pyfmt.F2(x.TotalSales), pyfmt.F2(x.TotalTax), job.ID), nil

	case "U1X", "REPORT_X2":
		x := st.GenerateXReport()
		job := s.recordReport(x, "X")
		return fmt.Sprintf("0|Reporte X2 #%d|Ventas: %s|Impreso:%d",
			x.Number, pyfmt.F2(x.TotalSales), job.ID), nil

	case "U0Z", "REPORT_Z":
		z := st.GenerateZReport()
		job := s.recordReport(z, "Z")
		return fmt.Sprintf("0|Reporte Z #%d|Ventas: %s|IVA: %s|Impreso:%d",
			z.Number, pyfmt.F2(z.TotalSales), pyfmt.F2(z.TotalTax), job.ID), nil

	case "U1Z", "REPORT_Z2":
		z := st.GenerateZReport()
		job := s.recordReport(z, "Z")
		return fmt.Sprintf("0|Reporte Z2 #%d|Ventas: %s|Impreso:%d",
			z.Number, pyfmt.F2(z.TotalSales), job.ID), nil
	}

	return "ERROR|0x50|Comando no implementado", nil
}

func paramString(params []any) string {
	if len(params) > 0 {
		if v, ok := params[0].(string); ok {
			return v
		}
	}
	return ""
}

func (s *Simulator) handleItem(raw, cmdType string, params []any) (string, error) {
	st := s.State
	if !st.DocumentOpen {
		st.OpenDocument("invoice")
	}

	switch cmdType {
	case "ITEM":
		if pyfmt.Count(raw) < 20 {
			return "ERROR|0x50|Item format invalid", nil
		}
		runes := []rune(raw)
		prefix := runes[0]
		taxMap := map[rune]string{' ': "exempt", '!': "general", '"': "reduced", '#': "additional"}
		taxType, ok := taxMap[prefix]
		if !ok {
			taxType = "general"
		}

		qtyStr := strings.TrimSpace(pyfmt.Slice(raw, 1, 9))
		priceStr := strings.TrimSpace(pyfmt.Slice(raw, 9, 19))
		desc := strings.TrimSpace(pyfmt.Slice(raw, 19, pyfmt.Count(raw)))

		qty, err := pyfmt.Float(qtyStr)
		if err != nil {
			return "ERROR|0x50|Invalid qty/price", nil
		}
		price, err := pyfmt.Float(priceStr)
		if err != nil {
			return "ERROR|0x50|Invalid qty/price", nil
		}
		if desc == "" {
			desc = "PRODUCTO"
		}
		item, err := st.AddItem(desc, qty, price, taxType)
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("0|Item|%s|%s|%s|%s|%s", desc,
			pyfmt.F3(item.Quantity), pyfmt.F2(item.Price),
			pyfmt.F2(item.Tax), pyfmt.F2(item.Total)), nil

	case "ITEM_CREDIT":
		if pyfmt.Count(raw) < 21 {
			return "ERROR|0x50|Credit note item format invalid", nil
		}
		taxTypeIdx := 1
		if len(params) > 0 {
			if v, ok := params[0].(int); ok {
				taxTypeIdx = v
			}
		}
		taxTypes := map[int]string{0: "exempt", 1: "general", 2: "reduced", 3: "additional"}
		taxType, ok := taxTypes[taxTypeIdx]
		if !ok {
			taxType = "general"
		}

		qtyStr := strings.TrimSpace(pyfmt.Slice(raw, 2, 10))
		priceStr := strings.TrimSpace(pyfmt.Slice(raw, 10, 20))
		desc := strings.TrimSpace(pyfmt.Slice(raw, 20, pyfmt.Count(raw)))

		qty, err := pyfmt.Float(qtyStr)
		if err != nil {
			return "ERROR|0x50|Invalid qty/price", nil
		}
		price, err := pyfmt.Float(priceStr)
		if err != nil {
			return "ERROR|0x50|Invalid qty/price", nil
		}
		if desc == "" {
			desc = "PRODUCTO NC"
		}
		item, err := st.AddItem(desc, qty, price, taxType)
		if err != nil {
			return "", err
		}
		block := st.CreditNoteTotals[taxType]
		block.Base += item.Base
		block.Tax += item.Tax
		st.CreditNoteTotals[taxType] = block
		return fmt.Sprintf("0|NC Item|%s|%s|%s|%s|%s", desc,
			pyfmt.F3(item.Quantity), pyfmt.F2(item.Price),
			pyfmt.F2(item.Tax), pyfmt.F2(item.Total)), nil

	case "ITEM_DEBIT":
		if pyfmt.Count(raw) < 21 {
			return "ERROR|0x50|Debit note item format invalid", nil
		}
		taxTypeIdx := 1
		if len(params) > 0 {
			if v, ok := params[0].(int); ok {
				taxTypeIdx = v
			}
		}
		taxTypes := map[int]string{0: "exempt", 1: "general", 2: "reduced", 3: "additional"}
		taxType, ok := taxTypes[taxTypeIdx]
		if !ok {
			taxType = "general"
		}

		qtyStr := strings.TrimSpace(pyfmt.Slice(raw, 2, 10))
		priceStr := strings.TrimSpace(pyfmt.Slice(raw, 10, 20))
		desc := strings.TrimSpace(pyfmt.Slice(raw, 20, pyfmt.Count(raw)))

		qty, err := pyfmt.Float(qtyStr)
		if err != nil {
			return "ERROR|0x50|Invalid qty/price", nil
		}
		price, err := pyfmt.Float(priceStr)
		if err != nil {
			return "ERROR|0x50|Invalid qty/price", nil
		}
		if desc == "" {
			desc = "PRODUCTO ND"
		}
		item, err := st.AddItem(desc, qty, price, taxType)
		if err != nil {
			return "", err
		}
		block := st.DebitNoteTotals[taxType]
		block.Base += item.Base
		block.Tax += item.Tax
		st.DebitNoteTotals[taxType] = block
		return fmt.Sprintf("0|ND Item|%s|%s|%s|%s|%s", desc,
			pyfmt.F3(item.Quantity), pyfmt.F2(item.Price),
			pyfmt.F2(item.Tax), pyfmt.F2(item.Total)), nil
	}

	return "ERROR|0x50|Unknown item type", nil
}

func resolveTaxName(spec string) string {
	s := strings.ToLower(strings.TrimSpace(spec))
	nameMap := map[string]string{
		"0": "exempt", "exempt": "exempt", "exento": "exempt",
		"1": "general", "general": "general",
		"2": "reduced", "reduced": "reduced", "reducida": "reduced",
		"3": "additional", "additional": "additional",
		"adicional": "additional",
		"":          "general",
	}
	if v, ok := nameMap[s]; ok {
		return v
	}
	value, err := pyfmt.Float(s)
	if err != nil {
		return "general"
	}
	if value == 0 {
		return "exempt"
	}
	if value == 16 {
		return "general"
	}
	if value == 8 {
		return "reduced"
	}
	if value == 30 {
		return "additional"
	}
	return "general"
}

func (s *Simulator) handleIxBatch(command string, params []string) (string, error) {
	st := s.State

	switch command {
	case "@OpenFiscalReceipt":
		st.OpenDocument("invoice")
		return "@Response|OK|0|Documento fiscal abierto", nil

	case "@OpenCreditNote":
		st.OpenDocument("credit_note")
		return "@Response|OK|0|Nota de credito abierta", nil

	case "@OpenDebitNote":
		st.OpenDocument("debit_note")
		return "@Response|OK|0|Nota de debito abierta", nil

	case "@OpenNonFiscalDoc":
		st.OpenDocument("non_fiscal")
		return "@Response|OK|0|Documento no fiscal abierto", nil

	case "@CloseNonFiscalDoc":
		if st.DocumentOpen {
			st.CloseDocument()
		}
		return "@Response|OK|0|DNF cerrado", nil

	case "@PrintLineItem", "@PrintLine":
		if !st.DocumentOpen {
			st.OpenDocument("invoice")
		}
		if len(params) >= 3 {
			desc := params[0]
			qty, err := pyfmt.Float(params[1])
			if err != nil {
				return "", err
			}
			price, err := pyfmt.Float(params[2])
			if err != nil {
				return "", err
			}
			taxSpec := "general"
			if len(params) > 3 {
				taxSpec = params[3]
			}
			taxName := resolveTaxName(taxSpec)
			item, err := st.AddItem(desc, qty, price, taxName)
			if err != nil {
				return "", err
			}
			return fmt.Sprintf("@Response|OK|0|%s|%s|%s|%s", desc,
				pyfmt.F3(qty), pyfmt.F2(price), pyfmt.F2(item.Total)), nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@RefundItem":
		if !st.DocumentOpen {
			return "@Response|Error|1|No document open", nil
		}
		if len(params) >= 4 {
			desc := params[0]
			qty, err := pyfmt.Float(params[1])
			if err != nil {
				return "", err
			}
			price, err := pyfmt.Float(params[2])
			if err != nil {
				return "", err
			}
			taxName := resolveTaxName(params[3])
			item, err := st.AddItem(desc, qty, price, taxName)
			if err != nil {
				return "", err
			}
			return fmt.Sprintf("@Response|OK|0|NC %s|%s|%s|%s", desc,
				pyfmt.F3(qty), pyfmt.F2(price), pyfmt.F2(item.Total)), nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@CustomerData", "@SetCustomerData":
		if len(params) >= 3 {
			st.CustomerRif = params[0]
			st.CustomerName = params[1]
			st.CustomerAddress = params[2]
		} else if len(params) == 2 {
			st.CustomerRif = params[0]
			st.CustomerName = params[1]
		} else if len(params) == 1 {
			st.CustomerRif = params[0]
		}
		return strings.TrimSpace("@Response|OK|0|Cliente " + st.CustomerRif + " " + st.CustomerName), nil

	case "@SetCustomerInfo1":
		if len(params) > 0 {
			st.CustomerName = params[0]
		} else {
			st.CustomerName = ""
		}
		return "@Response|OK|0|Nombre registrado", nil

	case "@SetCustomerInfo2":
		if len(params) > 0 {
			st.CustomerNameLine2 = params[0]
		} else {
			st.CustomerNameLine2 = ""
		}
		return "@Response|OK|0|Nombre linea 2 registrada", nil

	case "@SetCustomerTIN":
		if len(params) > 0 {
			st.CustomerRif = params[0]
		} else {
			st.CustomerRif = ""
		}
		return "@Response|OK|0|RIF registrado", nil

	case "@SetCustomerExtraData":
		return "@Response|OK|0|Datos extra registrados", nil

	case "@Subtotal":
		return fmt.Sprintf("@Response|OK|0|Subtotal: %s+IVA:%s",
			pyfmt.F2(st.SubtotalBases), pyfmt.F2(st.SubtotalTax)), nil

	case "@AddPayment", "@Cash":
		if len(params) >= 1 {
			amount, err := pyfmt.Float(params[0])
			if err != nil {
				return "", err
			}
			method := "cash"
			if len(params) > 1 {
				method = strings.ToLower(params[1])
			}
			methodMap := map[string]string{
				"efectivo": "cash", "cash": "cash", "money": "cash",
				"tarjeta": "card", "card": "card",
				"transferencia": "transfer", "transfer": "transfer",
				"credit": "credit", "credito": "credit",
				"cheque": "check", "check": "check",
			}
			if v, ok := methodMap[method]; ok {
				method = v
			}
			st.AddPayment(amount, method)
			return fmt.Sprintf("@Response|OK|0|Pago: %s|Pendiente: %s",
				pyfmt.F2(amount), pyfmt.F2(st.AmountPayable)), nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@TotalTender":
		if len(params) >= 2 {
			amount, err := pyfmt.Float(params[1])
			if err != nil {
				return "", err
			}
			if len(params) > 3 {
				discount, err := pyfmt.Float(params[3])
				if err != nil {
					return "", err
				}
				if discount > 0 {
					st.TotalDiscounts += discount
					st.AmountPayable -= discount
				}
			}
			st.AddPayment(amount, "cash")
			change := st.AmountPayable * -1
			if change < 0 {
				change = 0
			}
			return fmt.Sprintf("@Response|OK|0|Pago: %s|Vuelto: %s|%08d",
				pyfmt.F2(amount), pyfmt.F2(change), st.InvoiceCounter+1), nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@DirectPayment":
		if len(params) >= 1 {
			method, err := pyfmt.Int(params[0])
			if err != nil {
				return "", err
			}
			st.AddPayment(st.AmountPayable, fmt.Sprintf("pay_%d", method))
			return "@Response|OK|0|Pago directo", nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@RefundClose":
		if len(params) >= 2 {
			amount, err := pyfmt.Float(params[0])
			if err != nil {
				return "", err
			}
			if _, err := pyfmt.Int(params[1]); err != nil {
				return "", err
			}
			st.CloseDocument()
			return fmt.Sprintf("@Response|OK|0|Devolucion cerrada: %s", pyfmt.F2(amount)), nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@Cancel":
		if st.DocumentOpen {
			st.CloseDocument()
		}
		return "@Response|OK|0|Cancelado", nil

	case "@LastItemCancel":
		return "@Response|OK|0|Ultimo item cancelado", nil

	case "@LastItemDiscount":
		if len(params) >= 2 {
			amount, err := pyfmt.Float(params[0])
			if err != nil {
				return "", err
			}
			return fmt.Sprintf("@Response|OK|0|Descuento: %s", pyfmt.F2(amount)), nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@Close", "@CloseFiscalReceipt":
		if !st.DocumentOpen {
			return "@Response|OK|0|Cerrado", nil
		}
		doc := st.CloseDocument()
		if doc != nil {
			job := s.recordReceipt(doc)
			docNames := map[string]string{
				"invoice":     "Factura",
				"credit_note": "Nota de Credito",
				"debit_note":  "Nota de Debito",
			}
			docName, ok := docNames[doc.Type]
			if !ok {
				docName = "Documento"
			}
			return fmt.Sprintf("@Response|OK|0|%s %d cerrada|Total: %s|Impreso:%d",
				docName, doc.Number, pyfmt.F2(doc.Total), job.ID), nil
		}
		return "@Response|OK|0|Cerrado", nil

	case "@CloseCashReceipt":
		if st.DocumentOpen {
			doc := st.CloseDocument()
			if doc != nil {
				s.recordReceipt(doc)
			}
		}
		return "@Response|OK|0|DNF cerrado", nil

	case "@PrintXReport":
		x := st.GenerateXReport()
		job := s.recordReport(x, "X")
		return fmt.Sprintf("@Response|OK|0|Reporte X #%d|Ventas: %s|Impreso:%d",
			x.Number, pyfmt.F2(x.TotalSales), job.ID), nil

	case "@PrintZReport":
		z := st.GenerateZReport()
		job := s.recordReport(z, "Z")
		return fmt.Sprintf("@Response|OK|0|Reporte Z #%d|Ventas: %s|Impreso:%d",
			z.Number, pyfmt.F2(z.TotalSales), job.ID), nil

	case "@DailyClose":
		if len(params) >= 1 {
			closeType := params[0]
			z := st.GenerateZReport()
			job := s.recordReport(z, "Z")
			return fmt.Sprintf("@Response|OK|0|Cierre %s #%d|Impreso:%d",
				closeType, z.Number, job.ID), nil
		}
		return "@Response|Error|2|Invalid params", nil

	case "@DailyCloseByDate":
		z := st.GenerateZReport()
		job := s.recordReport(z, "Z")
		return fmt.Sprintf("@Response|OK|0|Cierre por fecha #%d|Impreso:%d",
			z.Number, job.ID), nil

	case "@DailyCloseByNumber":
		z := st.GenerateZReport()
		job := s.recordReport(z, "Z")
		return fmt.Sprintf("@Response|OK|0|Cierre por numero #%d|Impreso:%d",
			z.Number, job.ID), nil

	case "@PrintAuditStatusReport":
		return "@Response|OK|0|Reporte de auditoria impreso", nil

	case "@Reprint":
		return "@Response|OK|0|Reimpresion generada", nil

	case "@ReprintByDate":
		return "@Response|OK|0|Reimpresion por fecha", nil

	case "@ReprintByNumber":
		return "@Response|OK|0|Reimpresion por numero", nil

	case "@PrintFiscalText":
		text := ""
		if len(params) > 0 {
			text = params[0]
		}
		return "@Response|OK|0|Texto: " + text, nil

	case "@PrintNonFiscalText":
		text := ""
		if len(params) > 0 {
			text = params[0]
		}
		return "@Response|OK|0|No fiscal: " + text, nil

	case "@PrintCashItem":
		return "@Response|OK|0|Movimiento caja", nil

	case "@BarCode":
		return "@Response|OK|0|Codigo barras impreso", nil

	case "@Status", "@StatusRequest":
		status := st.GetStatusCode()
		err := st.GetErrorCode()
		docState := "CERRADO"
		if st.DocumentOpen {
			docState = "ABIERTO"
		}
		return fmt.Sprintf("@Response|OK|0|Status: 0x%02X|Error: 0x%02X|Doc: %s|Ventas: %s",
			status, err, docState, pyfmt.F2(st.DailySales)), nil

	case "@StatusExtra":
		return "@Response|OK|0|Status extra OK", nil

	case "@ConfigureControllerByOne":
		return "@Response|OK|0|Configuracion OK", nil

	case "@PrintConfigurationData":
		return "@Response|OK|0|Configuracion impresa", nil

	case "@ProgramClerk":
		return "@Response|OK|0|Cajero programado", nil

	case "@ProgramPaymentMedia":
		return "@Response|OK|0|Medio pago programado", nil

	case "@ProgramSymbol":
		return "@Response|OK|0|Simbolo programado", nil

	case "@ProgramTaxes":
		return "@Response|OK|0|Tasas programadas", nil

	case "@SaveTaxes":
		return "@Response|OK|0|Tasas guardadas", nil

	case "@SetDate":
		return "@Response|OK|0|Fecha establecida", nil

	case "@SetTime":
		return "@Response|OK|0|Hora establecida", nil

	case "@Login":
		return "@Response|OK|0|Logon OK", nil

	case "@Logoff":
		return "@Response|OK|0|Logoff OK", nil

	case "@TrainingMode":
		return "@Response|OK|0|Modo entrenamiento", nil

	case "@OpenDrawer":
		drawer := "1"
		if len(params) > 0 {
			drawer = params[0]
		}
		return "@Response|OK|0|Gaveta " + drawer + " abierta", nil

	case "@PrintTest":
		return "@Response|OK|0|Test impreso", nil

	case "@ResetPrinterBuffer":
		return "@Response|OK|0|Buffer reseteado", nil

	case "@SendRawCommand":
		return "@Response|OK|0|Raw enviado", nil

	case "@SetHeaderTrailer":
		return "@Response|OK|0|Header/trailer configurado", nil

	case "@DisplayCommercial":
		return "@Response|OK|0|Comercial mostrado", nil

	case "@DisplayDateTime":
		return "@Response|OK|0|Fecha/hora mostrada", nil

	case "@DisplayMessage":
		return "@Response|OK|0|Mensaje mostrado", nil

	case "@ProgramCommercial":
		return "@Response|OK|0|Comercial programado", nil

	case "@ProgramMessage":
		return "@Response|OK|0|Mensaje programado", nil

	case "@FormatCheck":
		return "@Response|OK|0|Cheque formateado", nil

	case "@FormatEndorse":
		return "@Response|OK|0|Endoso formateado", nil

	case "@ModeSlip":
		return "@Response|OK|0|Modo slip", nil

	case "@ModeValidation":
		return "@Response|OK|0|Modo validacion", nil

	case "@PrintEndorse":
		return "@Response|OK|0|Endoso impreso", nil

	case "@PrintValidation":
		return "@Response|OK|0|Validacion impresa", nil

	case "@ReadMICR":
		return "@Response|OK|0|MICR leido", nil
	}

	return "@Response|Error|0x50|Comando desconocido", nil
}
