# test-program

Research and evaluation documents (docs only — no integration code lives here).

| Document | Contents |
| --- | --- |
| [`docs/INTEGRATIONS_EVALUATION.md`](./docs/INTEGRATIONS_EVALUATION.md) | تقييم أدوات OSINT: Sherlock · Maigret · PhoneInfoga · OpenOSINT · Holehe |
| [`docs/AATM_ARENA_EVALUATION.md`](./docs/AATM_ARENA_EVALUATION.md) | تقييم مستودع AATM وموصل Arena، وتصميم وحدة `NEXUS Arena Bridge` ومحوّل `AATM Integration Adapter` الاختياريين |

## Tests

The documents carry content contracts enforced by stdlib-only tests (no third-party packages):

```bash
python3 -m unittest discover -s tests -t . -p 'test_*.py' -v
```

`tests/manual/probe_aatm_connector.py` is a manual evidence tool (not collected by the test
runner): point `AATM_REPO` at an AATM checkout to reproduce the connector measurements quoted in
`docs/AATM_ARENA_EVALUATION.md`.
