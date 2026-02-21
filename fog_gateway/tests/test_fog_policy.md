# Fog Gateway Policy Test Cases

1. **Good CSV (should forward)**
   - POST sample_good.csv to /upload
   - Expect HTTP 201 and JSON `status: forwarded`
   - Check `fog_gateway/forwarded_files/` contains a copy and a `.meta.json` with cloud response.

2. **Bad CSV (should quarantine)**
   - POST sample_bad.csv to /upload
   - Expect HTTP 200 and JSON `status: quarantined` and reason `high_null_pct`
   - Check `fog_gateway/quarantined_files/` for the file and `.meta.json` with summary.

3. **Parse error**
   - Send a non-CSV or malformed file (e.g., random text)
   - Expect HTTP 400 and `status: quarantined` with parse error.
   - Check `quarantined_files/`.

4. **Large file rejection**
   - Create a >5MB file and POST
   - Expect HTTP 413 (file_too_large).

5. **Cloud unavailable (simulate)**
   - Set forward.url to a non-routable port and POST a good CSV
   - Expect HTTP 202 `status: pending` and file saved in `pending_files/`.

Use `curl` or Postman to run these tests. Example:

```
curl -X POST http://localhost:5000/upload \
  -F "file=@sample_inputs/sample_good.csv" -F "client_id=test1"
```
