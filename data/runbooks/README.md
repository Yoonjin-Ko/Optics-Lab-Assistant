# 실험별 점검 문서 매핑

질문 키워드와 이전 대화로 `agent/optics.py`에서 문서 ID를 선택합니다.
MCP 리소스 `runbook://incident-response/{문서 ID}`가 같은 이름의 Markdown을 읽습니다.
파일명을 변경할 때는 `agent/optics.py`와 `tests/test_optics.py`도 함께 수정하세요.

| 실험 | 문서 | 문서 ID |
|---|---|---|
| 회절격자 및 프리즘 분광기 | [grating-prism-spectrometer.md](grating-prism-spectrometer.md) | `grating-prism-spectrometer` |
| 그림자와 회절 | [shadow-and-diffraction.md](shadow-and-diffraction.md) | `shadow-and-diffraction` |
| Michelson 간섭계 | [michelson-interferometer.md](michelson-interferometer.md) | `michelson-interferometer` |
| 렌즈와 광학장치 | [lenses-and-optical-instruments.md](lenses-and-optical-instruments.md) | `lenses-and-optical-instruments` |
| 빛의 편광과 반사 | [polarization-and-reflection.md](polarization-and-reflection.md) | `polarization-and-reflection` |
| 빛의 속도 | [speed-of-light.md](speed-of-light.md) | `speed-of-light` |
| 노광 치수 이상·범위 확인 | [lithography-cd.md](lithography-cd.md) | `lithography-cd` |
| 산란·하늘색 | [scattering-and-sky.md](scattering-and-sky.md) | `scattering-and-sky` |
| XRD·브래그 법칙 | [xrd-bragg.md](xrd-bragg.md) | `xrd-bragg` |
| 빛의 기초 지식 | [light-fundamentals.md](light-fundamentals.md) | `light-fundamentals` |
| 실험 종류·증상 확인 | [experiment-intake.md](experiment-intake.md) | `experiment-intake` |

## 노광·정밀장비 이해
- [빛으로 패턴 만들기](lithography-process.md)
- [해상도와 초점](resolution-and-focus.md)
- [패턴 품질 읽기](pattern-quality.md)
- [정렬 · 교정 · 검증](alignment-and-verification.md)


확인일: 2026-10-20. 원문 전체 수집이나 자동 갱신이 아닌 자체 요약입니다.

- [광흡수·광전효과](absorption-photoelectric.md): 밴드 간 들뜸과 표면 방출을 구분하는 가상 문턱 실험.

- [전자·에너지 준위](electron-energy-levels.md): 가전자대·전도대·페르미 준위·정공·일함수.
