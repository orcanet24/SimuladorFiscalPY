package protocol

import (
	"strconv"

	"simuladorfiscal/internal/pyfmt"
)

const (
	TFHKAOpenCreditNote    = "d1"
	TFHKAOpenDebitNote     = "d2"
	TFHKAOpenNonFiscal     = "80$"
	TFHKAPrintNonFiscalTx  = "80!"
	TFHKAPrintNonFiscalCnt = "80*"
	TFHKACloseNonFiscal    = "81"

	TFHKATaxExempt     = " "
	TFHKATaxGeneral    = "!"
	TFHKATaxReduced    = "\""
	TFHKATaxAdditional = "#"

	TFHKASubtotalPrint   = "3"
	TFHKASubtotalSilent  = "4"
	TFHKACloseTotalize   = "101"
	TFHKAOpenDrawer      = "0"
	TFHKAReportX         = "U0X"
	TFHKAReportX2        = "U1X"
	TFHKAReportZ         = "U0Z"
	TFHKAReportZ2        = "U1Z"
	TFHKAStatusS1        = "S1"
	TFHKAStatusS2        = "S2"
	TFHKAStatusS3        = "S3"
	TFHKAStatusS4        = "S4"
	TFHKAStatusS5        = "S5"
	TFHKAStatusS8E       = "S8E"
	TFHKAStatusS8P       = "S8P"
	TFHKAPago            = "100"
	TFHKAPagoDescription = "103"
	TFHKADescuento       = "700"
	TFHKARecargo         = "701"

	TFHKACreditNoteItemPrefix = "d"
	TFHKADebitNoteItemPrefix  = "`"

	TFHKAComment = "@COMENTARIO"

	TaxTypeExempt     = 0
	TaxTypeGeneral    = 1
	TaxTypeReduced    = 2
	TaxTypeAdditional = 3
)

const (
	HasarCommandPrefix     = "@"
	HasarOpenFiscalReceipt = "@OpenFiscalReceipt"
	HasarOpenCreditNote    = "@OpenCreditNote"
	HasarOpenDebitNote     = "@OpenDebitNote"
	HasarOpenNonFiscal     = "@OpenNonFiscalDoc"
	HasarPrintItem         = "@PrintLine"
	HasarPrintDescription  = "@PrintDescription"
	HasarPrintSubtotal     = "@Subtotal"
	HasarPayment           = "@AddPayment"
	HasarCash              = "@Cash"
	HasarClose             = "@Close"
	HasarCloseNonFiscal    = "@CloseNonFiscalDoc"
	HasarReportX           = "@PrintXReport"
	HasarReportZ           = "@PrintZReport"
	HasarReportMemory      = "@UploadReportMemory"
	HasarStatus            = "@Status"
	HasarCustomerData      = "@CustomerData"
	HasarComment           = "@Comment"
	HasarPrintText         = "@PrintText"
)

var STATUS_CODES = map[byte]string{
	0x00: "Estado desconocido",
	0x01: "Modo prueba - en espera",
	0x02: "Modo prueba - emision fiscal",
	0x03: "Modo prueba - emision no fiscal",
	0x04: "Modo fiscal - en espera",
	0x05: "Modo fiscal - emision fiscal",
	0x06: "Modo fiscal - emision no fiscal",
	0x07: "Fiscal casi llena - en espera",
	0x08: "Fiscal casi llena - emision fiscal",
	0x09: "Fiscal casi llena - emision no fiscal",
	0x0A: "Memoria fiscal llena - en espera",
	0x0B: "Memoria fiscal llena - emision fiscal",
	0x0C: "Memoria fiscal llena - emision no fiscal",
}

var ERROR_CODES = map[byte]string{
	0x00: "Sin error",
	0x01: "Fin papel",
	0x02: "Error mecanico papel",
	0x03: "Fin papel + error mecanico",
	0x50: "Comando invalido",
	0x54: "Tasa invalida",
	0x58: "Sin directivas",
	0x5C: "Comando invalido",
	0x60: "Error fiscal",
	0x64: "Error memoria fiscal",
	0x6C: "Memoria fiscal llena",
	0x70: "Buffer completo - reiniciar",
	0x80: "Error comunicacion",
	0x89: "Sin respuesta",
	0x90: "Error LRC",
	0x91: "Error interno API",
	0x99: "Error apertura archivo",
}

func GetStatusByte(mode, state, memory string) byte {
	if mode == "test" {
		switch state {
		case "waiting":
			return 0x01
		case "fiscal":
			return 0x02
		case "non_fiscal":
			return 0x03
		}
	} else {
		if memory == "ok" {
			switch state {
			case "waiting":
				return 0x04
			case "fiscal":
				return 0x05
			case "non_fiscal":
				return 0x06
			}
		} else if memory == "almost_full" {
			switch state {
			case "waiting":
				return 0x07
			case "fiscal":
				return 0x08
			case "non_fiscal":
				return 0x09
			}
		} else if memory == "full" {
			switch state {
			case "waiting":
				return 0x0A
			case "fiscal":
				return 0x0B
			case "non_fiscal":
				return 0x0C
			}
		}
	}
	return 0x04
}

func FormatLineItem(prefix string, qty, price float64, description string) string {
	return prefix + pyfmt.Fixed(qty, 8, 3) + pyfmt.Fixed(price, 10, 2) + description
}

func FormatCreditNoteItem(taxType int, qty, price float64, description string) string {
	return "d" + strconv.Itoa(taxType) + pyfmt.Fixed(qty, 8, 3) + pyfmt.Fixed(price, 10, 2) + description
}

func FormatDebitNoteItem(taxType int, qty, price float64, description string) string {
	return "`" + strconv.Itoa(taxType) + pyfmt.Fixed(qty, 8, 3) + pyfmt.Fixed(price, 10, 2) + description
}

func LineItemPrefix(taxRate float64) string {
	if taxRate == 0 {
		return " "
	} else if taxRate < 12 {
		return "\""
	} else if taxRate >= 16 {
		return "#"
	}
	return "!"
}
