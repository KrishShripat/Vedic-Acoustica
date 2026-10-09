const SHRUTIS = [
  'Sa', 'Re1', 'Re2', 'Re3', 'Re4',
  'Ga1', 'Ga2', 'Ga3', 'Ga4',
  'Ma1', 'Ma2', 'Ma3', 'Ma4',
  'Pa', 'Dha1', 'Dha2', 'Dha3', 'Dha4',
  'Ni1', 'Ni2', 'Ni3', 'Ni4',
]

const FAMILIES = ['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni']

function familyFor(shruti) {
  return FAMILIES.find(family => shruti.startsWith(family)) || 'Sa'
}

export default function ShrutiInstrument({ selectedSwara, detectedSwaras = [], onSelect }) {
  const detectedNames = new Set(detectedSwaras.map(item => item.swara))

  return (
    <section className="instrument-panel" aria-label="Interactive 22 Shruti acoustic instrument">
      <div className="instrument-heading">
        <span className="eyebrow">The 22-fold scale</span>
        <span className="instrument-index">ŚRUTI YANTRA · I</span>
      </div>
      <div className="instrument-stage">
        <div className="instrument-wheel">
          <div className="wheel-engraving" aria-hidden="true" />
          <svg className="wheel-geometry" viewBox="0 0 500 500" aria-hidden="true">
            <circle cx="250" cy="250" r="212" />
            <circle cx="250" cy="250" r="177" />
            <circle cx="250" cy="250" r="132" />
            {SHRUTIS.map((_, index) => {
              const angle = (index / SHRUTIS.length) * Math.PI * 2 - Math.PI / 2
              const inner = 139
              const outer = index % 3 === 0 ? 210 : 199
              return (
                <line
                  key={index}
                  x1={250 + Math.cos(angle) * inner}
                  y1={250 + Math.sin(angle) * inner}
                  x2={250 + Math.cos(angle) * outer}
                  y2={250 + Math.sin(angle) * outer}
                />
              )
            })}
            <path d="M250 78 422 250 250 422 78 250Z" />
            <path d="M250 118 382 250 250 382 118 250Z" />
          </svg>
          {SHRUTIS.map((shruti, index) => {
            const angle = (index / SHRUTIS.length) * Math.PI * 2 - Math.PI / 2
            const radius = 43
            const left = 50 + (Math.cos(angle) * radius)
            const top = 50 + (Math.sin(angle) * radius)
            const isDetected = detectedNames.has(shruti)
            const isSelected = selectedSwara === shruti
            return (
              <button
                key={shruti}
                type="button"
                className={`shruti-mark ${isSelected ? 'is-selected' : ''} ${isDetected ? 'is-detected' : ''}`}
                style={{ left: `${left}%`, top: `${top}%`, '--family-tone': `var(--tone-${familyFor(shruti)})` }}
                onClick={() => onSelect(shruti)}
                aria-pressed={isSelected}
                aria-label={`${shruti}${isDetected ? ', detected in this recording' : ''}`}
                title={isDetected ? `${shruti} · detected in analysis` : shruti}
              >
                {shruti}
              </button>
            )
          })}
          <div className="instrument-heart">
            <span className="heart-caption">SWARA</span>
            <strong>{selectedSwara}</strong>
            <span className="heart-rule" />
            <span className="heart-caption">
              {detectedNames.has(selectedSwara) ? 'FOUND IN RECORDING' : 'SELECTED DEGREE'}
            </span>
          </div>
        </div>
      </div>
      <div className="instrument-legend">
        {FAMILIES.map(family => (
          <span className="legend-entry" key={family}>
            <i style={{ '--family-tone': `var(--tone-${family})` }} />
            {family}
          </span>
        ))}
      </div>
      <p className="instrument-note">
        {detectedNames.size
          ? `${detectedNames.size} swara${detectedNames.size === 1 ? '' : 's'} marked from this analysis`
          : 'Select an engraved degree to inspect the 22-step scale'}
      </p>
    </section>
  )
}
