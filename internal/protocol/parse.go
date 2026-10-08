package protocol

import (
	"strings"

	"simuladorfiscal/internal/pyfmt"
)

func ParseIxBatch(data string) (string, []string, bool) {
	if !strings.HasPrefix(data, "@") {
		return "", nil, false
	}
	parts := strings.Split(data, "|")
	command := strings.TrimSpace(parts[0])
	var params []string
	if len(parts) > 1 {
		params = make([]string, 0, len(parts)-1)
		for _, p := range parts[1:] {
			params = append(params, strings.TrimSpace(p))
		}
	}
	return command, params, true
}

func ParseTFHKA(data string) (string, []any, error) {
	data = strings.TrimSpace(data)
	if data == "" {
		return "", nil, nil
	}

	switch data {
	case "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8E", "S8P":
		return data, nil, nil
	case "U0X", "U1X", "U0Z", "U1Z":
		return data, nil, nil
	case "3":
		return "SUBTOTAL_PRINT", nil, nil
	case "4":
		return "SUBTOTAL_SILENT", nil, nil
	case "101":
		return "CLOSE_TOTALIZE", nil, nil
	case "0":
		return "OPEN_DRAWER", nil, nil
	case "d1":
		return "OPEN_CREDIT_NOTE", nil, nil
	case "d2":
		return "OPEN_DEBIT_NOTE", nil, nil
	case "80$":
		return "OPEN_NON_FISCAL", nil, nil
	case "81":
		return "CLOSE_NON_FISCAL", nil, nil
	}

	runes := []rune(data)

	if strings.HasPrefix(data, "d") && len(runes) > 2 {
		taxType, err := parseTaxType(runes[1])
		if err != nil {
			return "", nil, err
		}
		return "ITEM_CREDIT", []any{taxType}, nil
	}

	if strings.HasPrefix(data, "`") && len(runes) > 2 {
		taxType, err := parseTaxType(runes[1])
		if err != nil {
			return "", nil, err
		}
		return "ITEM_DEBIT", []any{taxType}, nil
	}

	if strings.HasPrefix(data, "@COMENTARIO") {
		return "COMMENT", []any{strings.TrimSpace(data[len("@COMENTARIO"):])}, nil
	}

	if len(runes) > 0 {
		switch runes[0] {
		case ' ', '!', '"', '#':
			taxMap := map[rune]int{' ': 0, '!': 1, '"': 2, '#': 3}
			return "ITEM", []any{taxMap[runes[0]]}, nil
		}
	}

	if strings.HasPrefix(data, "80!") {
		return "PRINT_NON_FISCAL_TEXT", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "80*") {
		return "PRINT_NON_FISCAL_CONTENT", []any{data[3:]}, nil
	}

	if strings.HasPrefix(data, "100") {
		return "PAYMENT", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "103") {
		return "PAYMENT_DESC", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "700") {
		return "DISCOUNT", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "701") {
		return "SURCHARGE", []any{data[3:]}, nil
	}

	if strings.HasPrefix(data, "iR*") {
		return "CUSTOMER_RIF", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "iS*") {
		return "CUSTOMER_NAME", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "i01") {
		return "CUSTOMER_ADDRESS", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "i02") {
		return "CUSTOMER_PHONE", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "iF*") {
		return "INVOICE_NUMBER", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "iD*") {
		return "INVOICE_DATE", []any{data[3:]}, nil
	}
	if strings.HasPrefix(data, "iI*") {
		return "FISCAL_SERIAL", []any{data[3:]}, nil
	}

	return "UNKNOWN", []any{data}, nil
}

func parseTaxType(r rune) (int, error) {
	if pyfmt.PyIsDigit(r) {
		return pyfmt.Int(string(r))
	}
	return 1, nil
}
