export const mockSummary = {
  total_active_visits: 23,
  total_waiting_patients: 18,
  average_wait_minutes: 14,
  areas_at_risk: 2,
};

export const mockAreas = [
  {
    area_id: "area-001",
    area_name: "Laboratorio",
    current_queue_length: 8,
    estimated_wait_minutes: 22,
    people_in_area: 6, // from CV worker
    status: "saturated", // "normal" | "warning" | "saturated"
  },
  {
    area_id: "area-002",
    area_name: "Ultrasonido",
    current_queue_length: 3,
    estimated_wait_minutes: 12,
    people_in_area: 2,
    status: "normal",
  },
  {
    area_id: "area-003",
    area_name: "Rayos X",
    current_queue_length: 5,
    estimated_wait_minutes: 18,
    people_in_area: 4,
    status: "warning",
  },
  {
    area_id: "area-004",
    area_name: "Electrocardiograma",
    current_queue_length: 1,
    estimated_wait_minutes: 5,
    people_in_area: 1,
    status: "normal",
  },
];

export const mockActiveVisits = [
  {
    visit_id: "v-001",
    patient_name: "María García",
    current_area: "Laboratorio",
    step_order: 1,
    total_steps: 2,
    status: "in_progress",
    waiting_since_minutes: 8,
  },
  {
    visit_id: "v-002",
    patient_name: "Carlos López",
    current_area: "Ultrasonido",
    step_order: 2,
    total_steps: 2,
    status: "in_progress",
    waiting_since_minutes: 3,
  },
  {
    visit_id: "v-003",
    patient_name: "Ana Martínez",
    current_area: "Rayos X",
    step_order: 1,
    total_steps: 1,
    status: "in_progress",
    waiting_since_minutes: 12,
  },
  {
    visit_id: "v-004",
    patient_name: "Luis Hernández",
    current_area: "Laboratorio",
    step_order: 1,
    total_steps: 3,
    status: "in_progress",
    waiting_since_minutes: 5,
  },
  {
    visit_id: "v-005",
    patient_name: "Rosa Sánchez",
    current_area: "Electrocardiograma",
    step_order: 1,
    total_steps: 1,
    status: "in_progress",
    waiting_since_minutes: 2,
  },
];

// 12 data points = last 60 minutes (one per 5 min)
export const mockWaitTimeHistory = {
  labels: [
    "55m",
    "50m",
    "45m",
    "40m",
    "35m",
    "30m",
    "25m",
    "20m",
    "15m",
    "10m",
    "5m",
    "ahora",
  ],
  series: {
    Laboratorio: [18, 20, 22, 25, 24, 22, 20, 22, 24, 26, 24, 22],
    Ultrasonido: [10, 12, 11, 13, 14, 12, 11, 12, 13, 12, 11, 12],
    "Rayos X": [15, 16, 18, 17, 16, 18, 19, 18, 17, 18, 18, 18],
    Electrocardiograma: [4, 5, 4, 5, 5, 4, 5, 5, 4, 5, 5, 5],
  },
};

export const mockAlerts = [
  {
    id: "a-001",
    severity: "critical",
    area_name: "Laboratorio",
    message: "Cola de 8 pacientes. Capacidad máxima alcanzada.",
    triggered_at: new Date(Date.now() - 5 * 60000).toISOString(),
  },
  {
    id: "a-002",
    severity: "warning",
    area_name: "Rayos X",
    message: "Espera estimada supera 15 minutos.",
    triggered_at: new Date(Date.now() - 12 * 60000).toISOString(),
  },
  {
    id: "a-003",
    severity: "info",
    area_name: "Ultrasonido",
    message: "Paciente urgente en cola.",
    triggered_at: new Date(Date.now() - 2 * 60000).toISOString(),
  },
];
