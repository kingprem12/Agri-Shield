# ER Diagram

```mermaid
erDiagram
    PREDICTION_HISTORY {
        int id PK
        string state
        string district
        float latitude
        float longitude
        float ndvi
        float lst
        float rainfall
        float temperature
        float humidity
        float wind_speed
        float soil_moisture_proxy
        string severity
        float probability
        float risk_score
        datetime created_at
    }
```

