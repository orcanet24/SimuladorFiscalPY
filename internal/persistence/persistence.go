package persistence

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"time"

	"simuladorfiscal/internal/state"
)

type fileFormat struct {
	SavedAt      string               `json:"saved_at"`
	Brand        string               `json:"brand"`
	Model        string               `json:"model"`
	CommandCount int                  `json:"command_count"`
	History      []state.HistoryEntry `json:"history"`
	*state.State
}

func Save(path, brand, model string, commandCount int, history []state.HistoryEntry, st *state.State) error {
	if path == "" {
		return nil
	}
	if history == nil {
		history = []state.HistoryEntry{}
	}
	if len(history) > 500 {
		history = history[len(history)-500:]
	}
	f := &fileFormat{
		SavedAt:      time.Now().Format("2006-01-02T15:04:05.999999"),
		Brand:        brand,
		Model:        model,
		CommandCount: commandCount,
		History:      history,
		State:        st,
	}
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", " ")
	if err := enc.Encode(f); err != nil {
		return err
	}
	out := bytes.TrimRight(buf.Bytes(), "\n")
	directory := filepath.Dir(path)
	if err := os.MkdirAll(directory, 0o755); err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, out, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func Load(path string, st *state.State) (int, []state.HistoryEntry, bool) {
	if path == "" {
		return 0, nil, false
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return 0, nil, false
	}
	f := &fileFormat{State: st}
	if err := json.Unmarshal(data, f); err != nil {
		return 0, nil, false
	}
	if st.Company.Rif != "" {
		st.Rif = st.Company.Rif
		st.FiscalRegistration = st.Company.Rif
	}
	if !st.DocumentOpen {
		st.CurrentState = "waiting"
		st.CurrentItems = []state.Item{}
		st.DocumentType = ""
	}
	history := f.History
	if history == nil {
		history = []state.HistoryEntry{}
	}
	return f.CommandCount, history, true
}
