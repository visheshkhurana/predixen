# Testing Quick Start Guide

## File Locations

- **Audit Reports**: 
  - `/TEST_COVERAGE_SUMMARY.md` - Start here (2-minute read)
  - `/TEST_COVERAGE_AUDIT.md` - Full detailed report (30-minute read)

- **Existing Tests**:
  - `/server/tests/` - 4 test files (95 test cases)
  - `/client/src/lib/__tests__/` - 2 test files
  - `/qa-lab/` - Integration tests

## Current Coverage by Module

```
Financial Calculations:  ████████░░  60%  (GOOD)
Data Integrity:          ███░░░░░░░  30%  (FAIR)
QA Lab Integration:      ██████████ 100%  (EXCELLENT)
Frontend Utils:          ████░░░░░░  40%  (FAIR)
API Endpoints:           ░░░░░░░░░░   1%  (CRITICAL GAP)
Data Ingestion:          ░░░░░░░░░░   5%  (CRITICAL GAP)
Monte Carlo:             ░░░░░░░░░░   0%  (CRITICAL GAP)
Connectors:              ░░░░░░░░░░   0%  (CRITICAL GAP)
Copilot:                 ░░░░░░░░░░   5%  (HIGH GAP)
Frontend Components:     ░░░░░░░░░░   1%  (CRITICAL GAP)
```

## What to Test First

### TIER 1 (This Sprint) - CRITICAL
1. **Extend financial calculation tests** (20 new tests)
   - File: `server/tests/test_financial_calculations.py`
   - Add: negative cash, extreme values, rounding

2. **Create Monte Carlo simulation tests** (40 new tests)
   - File: `server/tests/test_monte_carlo_simulation.py`
   - Add: distribution generation, percentiles, variance

3. **Create data ingestion tests** (80 new tests)
   - File: `server/tests/test_data_ingestion.py`
   - Add: CSV, Excel, PDF parsing, classifier accuracy

4. **Create auth tests** (40 new tests)
   - File: `server/tests/test_auth_endpoints.py`
   - Add: login, JWT, permissions, roles

### TIER 2 (Next Sprint) - HIGH PRIORITY
5. **API endpoint tests** (150 new tests)
6. **Connector sync tests** (100 new tests)

### TIER 3 (Future) - MEDIUM PRIORITY
7. **Copilot intent tests** (50 new tests)
8. **Frontend component tests** (100+ new tests)

## Running Tests

### Backend (Python)
```bash
# List available tests
cd "/sessions/charming-zen-brown/mnt/Fund-Flow 3/"
python -m pytest --collect-only

# Run all tests
python -m pytest server/tests/ -v

# Run specific test file
python -m pytest server/tests/test_financial_calculations.py -v

# Run with coverage
python -m pytest server/tests/ --cov=server --cov-report=html
```

### Frontend (TypeScript)
```bash
cd "/sessions/charming-zen-brown/mnt/Fund-Flow 3/"

# Run Vitest tests
npm test

# Run specific test
npm test money.test.ts

# Run with coverage
npm test -- --coverage
```

## Test File Locations

### Backend Tests
- `/server/tests/test_financial_calculations.py` (306 lines, 30 tests)
- `/server/tests/test_canonical_data_flow.py` (172 lines, 16 tests)
- `/server/tests/test_copilot_trust.py` (202 lines, 18 tests)
- `/server/tests/test_truth_scan.py` (259 lines, 31 tests)

### Frontend Tests
- `/client/src/lib/__tests__/money.test.ts` (76 lines)
- `/client/src/lib/__tests__/finance.test.ts` (61 lines)

### Integration Tests
- `/qa-lab/runner/` - Test executor
- `/qa-lab/scenarios/` - Scenario definitions
- `/qa-lab/datasets/` - Sample financial data
- `/qa-lab/latest-report.md` - Most recent results

## Key Modules to Test

### Critical Path (Untested)
| Module | Location | Files | Priority |
|--------|----------|-------|----------|
| Data Ingestion | `/server/ingest/` | 6 | P0 |
| Monte Carlo | `/server/simulate/` | 2 | P0 |
| API Endpoints | `/server/api/` | 52 | P0 |
| Auth/Permissions | `/server/api/auth.py` | 1 | P0 |
| Connectors | `/server/connectors/` | 36 | P1 |
| Copilot Intent | `/server/copilot/` | 20 | P1 |
| Frontend Components | `/client/src/` | 13+ dirs | P2 |

### Well-Tested (Don't Need Much)
- Financial calculations (60% done)
- Data integrity/hashing
- QA Lab integration

## Common Test Patterns

### Test Financial Calculations
```python
def test_burn_formula():
    revenue = 1000.0
    expenses = 1500.0
    net_burn = calculate_net_burn(expenses, revenue)
    assert net_burn == 500.0
    assert determine_burn_status(net_burn) == BurnStatus.BURNING
```

### Test API Endpoints
```python
def test_login_valid():
    response = client.post("/auth/login", 
        json={"email": "user@example.com", "password": "password"})
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Test Data Transformations
```python
def test_excel_extraction():
    df = extract_excel(sample_file)
    assert len(df) == 100  # 100 rows
    assert "Revenue" in df.columns
    assert df["Revenue"].dtype == float
```

## Useful Links

- **Pytest Docs**: https://docs.pytest.org/
- **FastAPI Testing**: https://fastapi.tiangolo.com/advanced/testing/
- **Vitest Docs**: https://vitest.dev/
- **React Testing Library**: https://testing-library.com/docs/react-testing-library/intro/

## Configuration Files

- **pytest.ini**: `./pytest.ini`
- **pyproject.toml**: `./pyproject.toml`
- **Vite Config**: `./vite.config.ts` (no vitest config yet)

## Next Steps

1. Read `/TEST_COVERAGE_SUMMARY.md` (5 min)
2. Read relevant sections of `/TEST_COVERAGE_AUDIT.md` (15 min)
3. Run existing tests: `python -m pytest server/tests/ -v`
4. Pick one Tier 1 module and write 20 new tests
5. Add to CI/CD pipeline

## Questions?

Reference the full audit report: `/TEST_COVERAGE_AUDIT.md`

---

Last Updated: 2026-02-21
