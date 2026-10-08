package simulator

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"simuladorfiscal/internal/persistence"
	"simuladorfiscal/internal/protocol"
	"simuladorfiscal/internal/pyfmt"
	"simuladorfiscal/internal/render"
	"simuladorfiscal/internal/state"
)

type ErrorEntry struct {
	Command   string
	Error     string
	Timestamp time.Time
}

type Simulator struct {
	Brand        string
	Model        string
	State        *state.State
	CommandCount int
	ErrorLog     []ErrorEntry
	History      []state.HistoryEntry
	StatePath    string

	mu sync.Mutex
}

type brandConfig struct {
	serial      string
	fiscalReg   string
	memoryTotal float64
	taxRates    map[string]float64
}

var brandConfigs = map[string]brandConfig{
	"TFHKA": {
		serial: "MLTFHKA001", fiscalReg: "J-12345678-9", memoryTotal: 4.0,
		taxRates: map[string]float64{"general": 16.0, "reduced": 8.0, "additional": 30.0},
	},
	"HASAR": {
		serial: "MLHSR615F001", fiscalReg: "J-98765432-1", memoryTotal: 4.0,
		taxRates: map[string]float64{"general": 16.0, "reduced": 8.0, "additional": 30.0},
	},
	"BIXOLON": {
		serial: "MLBLN270001", fiscalReg: "J-55556666-3", memoryTotal: 2.0,
		taxRates: map[string]float64{"general": 16.0, "reduced": 8.0, "additional": 30.0},
	},
	"EPSON": {
		serial: "MLSTM200001", fiscalReg: "J-44443333-5", memoryTotal: 8.0,
		taxRates: map[string]float64{"general": 16.0, "reduced": 8.0, "additional": 30.0},
	},
}

var defaultModels = map[string]string{
	"TFHKA":   "TFHKA",
	"HASAR":   "SMH/P-615F",
	"BIXOLON": "SRP-270",
	"EPSON":   "TM2000",
}

func CreateSimulator(brand, model, statePath string) (*Simulator, error) {
	brandLower := strings.ToLower(brand)
	brandU := strings.ToUpper(brandLower)
	if _, ok := brandConfigs[brandU]; !ok {
		return nil, fmt.Errorf("Unknown brand '%s'. Supported: ['tfhka', 'hasar', 'bixolon', 'epson']", brand)
	}
	if model == "" {
		model = defaultModels[brandU]
	}
	return newSimulator(brand, model, statePath), nil
}

func newSimulator(brand, model, statePath string) *Simulator {
	brandU := strings.ToUpper(brand)
	st := state.NewState(brand, model)
	s := &Simulator{
		Brand:     brandU,
		Model:     strings.ToUpper(model),
		State:     st,
		StatePath: statePath,
	}
	s.configureBrand()
	if statePath != "" {
		count, history, ok := persistence.Load(statePath, st)
		if ok {
			s.CommandCount = count
			s.History = history
		}
	}
	return s
}

func (s *Simulator) configureBrand() {
	config, ok := brandConfigs[s.Brand]
	if !ok {
		config = brandConfigs["TFHKA"]
	}
	s.State.SerialNumber = config.serial
	s.State.FiscalRegistration = config.fiscalReg
	s.State.Rif = config.fiscalReg
	s.State.AuditMemoryTotal = config.memoryTotal
	s.State.AuditMemoryFree = config.memoryTotal * 0.9
	rates := make(map[string]float64, len(config.taxRates))
	for k, v := range config.taxRates {
		rates[k] = v
	}
	s.State.TaxRates = rates
}

func (s *Simulator) ProcessCommand(command string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.CommandCount++
	var response string
	func() {
		defer func() {
			if r := recover(); r != nil {
				s.ErrorLog = append(s.ErrorLog, ErrorEntry{
					Command: command, Error: fmt.Sprintf("%v", r), Timestamp: time.Now(),
				})
				response = s.formatResponse(fmt.Sprintf("ERROR|0x50|%v", r))
			}
		}()
		resp, err := s.executeCommand(command)
		if err != nil {
			s.ErrorLog = append(s.ErrorLog, ErrorEntry{
				Command: command, Error: err.Error(), Timestamp: time.Now(),
			})
			response = s.formatResponse("ERROR|0x50|" + err.Error())
		} else {
			response = s.formatResponse(resp)
		}
	}()
	s.logHistory(command, response)
	s.saveState()
	return response
}

func (s *Simulator) formatResponse(response string) string {
	if s.Brand == "EPSON" {
		status := s.State.GetStatusCode()
		err := s.State.GetErrorCode()
		return fmt.Sprintf("0x%02X|0x%02X|%s", status, err, response)
	}
	return response
}

func (s *Simulator) logHistory(command, response string) {
	entry := state.HistoryEntry{
		Seq:      s.CommandCount,
		TS:       time.Now().Format("2006-01-02T15:04:05.000"),
		Command:  command,
		Response: response,
		OK:       !strings.Contains(response, "Error") && !strings.Contains(response, "ERROR"),
	}
	s.History = append(s.History, entry)
	if len(s.History) > 1000 {
		s.History = s.History[len(s.History)-1000:]
	}
}

func (s *Simulator) saveState() {
	if s.StatePath == "" {
		return
	}
	if err := persistence.Save(s.StatePath, s.Brand, s.Model, s.CommandCount, s.History, s.State); err != nil {
		log.Printf("Could not save state to %s: %s", s.StatePath, err)
	}
}

func (s *Simulator) executeCommand(command string) (string, error) {
	if strings.HasPrefix(command, "@") && !strings.HasPrefix(command, "@COMENTARIO") {
		ixcmd, ixparams, ok := protocol.ParseIxBatch(command)
		if ok && ixcmd != "" {
			return s.handleIxBatch(ixcmd, ixparams)
		}
		return "@Response|Error|0x50|Comando desconocido", nil
	}

	cmdType, params, err := protocol.ParseTFHKA(command)
	if err != nil {
		return "", err
	}
	if cmdType != "" && cmdType != "UNKNOWN" {
		return s.handleTFHKA(cmdType, params, command)
	}
	return "ERROR|0x50|Comando desconocido", nil
}

func (s *Simulator) recordPaper(kind, title string, lines []string, meta map[string]any) *state.PrintJob {
	if meta == nil {
		meta = map[string]any{}
	}
	job := &state.PrintJob{
		ID:    s.State.PrintJobSeq + 1,
		Kind:  kind,
		Title: title,
		TS:    time.Now().Format("2006-01-02T15:04:05"),
		Brand: s.Brand,
		Lines: lines,
		Meta:  meta,
	}
	s.State.PrintJobSeq++
	s.State.PrintJobs = append(s.State.PrintJobs, job)
	if len(s.State.PrintJobs) > 200 {
		s.State.PrintJobs = s.State.PrintJobs[len(s.State.PrintJobs)-200:]
	}
	return job
}

func (s *Simulator) recordReceipt(doc *state.Document) *state.PrintJob {
	company := doc.Company
	docType := doc.Type
	kind := "receipt"
	if docType != "invoice" {
		kind = docType
	}
	titles := map[string]string{
		"invoice":     fmt.Sprintf("FACTURA FISCAL N° %08d", doc.Number),
		"credit_note": fmt.Sprintf("NOTA DE CREDITO N° %08d", doc.Number),
		"debit_note":  fmt.Sprintf("NOTA DE DEBITO N° %08d", doc.Number),
		"non_fiscal":  fmt.Sprintf("DOC NO FISCAL N° %08d", doc.Number),
	}
	title, ok := titles[docType]
	if !ok {
		title = "Documento"
	}
	var lines []string
	if docType == "non_fiscal" {
		lines = render.RenderNonFiscal(doc, company)
	} else {
		lines = render.RenderReceipt(doc, company)
	}
	meta := map[string]any{
		"number":   doc.Number,
		"total":    pyfmt.PyRound(doc.Total, 2),
		"doc_type": docType,
	}
	return s.recordPaper(kind, title, lines, meta)
}

func (s *Simulator) recordReport(rep *state.Report, kind string) *state.PrintJob {
	var title string
	var lines []string
	if kind == "X" {
		title = fmt.Sprintf("REPORTE X N° %04d", rep.Number)
		lines = render.RenderXReport(rep, s.State.Company)
	} else {
		title = fmt.Sprintf("REPORTE Z N° %04d", rep.Number)
		lines = render.RenderZReport(rep, s.State.Company)
	}
	meta := map[string]any{
		"number":      rep.Number,
		"total_sales": pyfmt.PyRound(rep.TotalSales, 2),
		"total_tax":   pyfmt.PyRound(rep.TotalTax, 2),
	}
	return s.recordPaper(strings.ToLower(kind)+"_report", title, lines, meta)
}

func (s *Simulator) ProgramCompany(data map[string]any) state.Company {
	s.mu.Lock()
	defer s.mu.Unlock()
	result := s.State.ProgramCompany(data)
	s.saveState()
	return result
}

func (s *Simulator) CancelLocalDocument() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.State.DocumentOpen {
		return false
	}
	s.State.DocumentOpen = false
	s.State.DocumentType = ""
	s.State.CurrentState = "waiting"
	s.State.CurrentItems = []state.Item{}
	s.State.SubtotalBases = 0.0
	s.State.SubtotalTax = 0.0
	s.State.AmountPayable = 0.0
	return true
}

func (s *Simulator) HistorySince(since int) ([]state.HistoryEntry, int) {
	s.mu.Lock()
	defer s.mu.Unlock()
	entries := []state.HistoryEntry{}
	for _, e := range s.History {
		if e.Seq > since {
			entries = append(entries, e)
		}
	}
	return entries, s.CommandCount
}

func (s *Simulator) PreviewLines() (bool, []string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.State.DocumentOpen, render.RenderOpenDocument(s.State)
}

func (s *Simulator) JobsMeta() []map[string]any {
	s.mu.Lock()
	defer s.mu.Unlock()
	jobs := []map[string]any{}
	for i := len(s.State.PrintJobs) - 1; i >= 0; i-- {
		j := s.State.PrintJobs[i]
		jobs = append(jobs, map[string]any{
			"id": j.ID, "kind": j.Kind, "title": j.Title,
			"ts": j.TS, "meta": j.Meta,
		})
	}
	return jobs
}

func (s *Simulator) FindJob(id int) (*state.PrintJob, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, j := range s.State.PrintJobs {
		if j.ID == id {
			return j, true
		}
	}
	return nil, false
}

func (s *Simulator) LastJobID() (any, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.State.PrintJobs) == 0 {
		return nil, false
	}
	return s.State.PrintJobs[len(s.State.PrintJobs)-1].ID, true
}

func (s *Simulator) WithLock(fn func()) {
	s.mu.Lock()
	defer s.mu.Unlock()
	fn()
}
