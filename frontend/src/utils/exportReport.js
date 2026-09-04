import { jsPDF } from 'jspdf'
import Plotly from 'plotly.js-dist'

const CHART_DEFS = [
  { id: 'chart-spectrogram', title: 'Spectrogram' },
  { id: 'chart-clusters', title: 'Shruti Clusters (K=22)' },
  { id: 'chart-shruti-map', title: '22 Shruti Frequency Map' },
  { id: 'chart-ghana-path', title: 'Ghana Patha Validation' },
  { id: 'chart-raga-detection', title: 'Raga Detection' },
]

async function findGraphDiv(chartId) {
  const deadline = Date.now() + 3000
  while (Date.now() < deadline) {
    const card = document.getElementById(chartId)
    const graphDiv = card?.querySelector('.js-plotly-plot')
    if (graphDiv) return graphDiv
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  throw new Error(`Chart "${chartId}" is not rendered yet. Wait for all charts to finish drawing, then try again.`)
}

async function captureChart(chartId) {
  const graphDiv = await findGraphDiv(chartId)
  const dataUrl = await Plotly.toImage(graphDiv, {
    format: 'png',
    width: 900,
    height: 400,
    scale: 2,
  })
  return dataUrl
}

function summaryRows(analysis) {
  const rows = [
    ['Ghana Patha', analysis.ghana_patha_valid ? 'Valid' : 'Invalid'],
  ]
  if (typeof analysis.ghana_patha_confidence === 'number') {
    rows.push(['Confidence', `${(analysis.ghana_patha_confidence * 100).toFixed(1)}%`])
  }
  if (analysis.raga_detection?.best_match) {
    const rm = analysis.raga_detection.best_match
    rows.push(['Raga', `${rm.raga_name} (${rm.tradition})`])
    rows.push(['Raga Match', `${(rm.confidence * 100).toFixed(1)}%`])
  } else if (analysis.raga_detection) {
    rows.push(['Raga', 'No confident match'])
  }
  if (typeof analysis.tempo === 'number') {
    rows.push(['Tempo', `${analysis.tempo.toFixed(1)} BPM`])
  }
  if (typeof analysis.duration === 'number') {
    rows.push(['Duration', `${analysis.duration.toFixed(1)} s`])
  }
  if (analysis.dominant_frequencies) {
    rows.push(['Frequency samples', String(analysis.dominant_frequencies.length)])
  }
  return rows
}

export default async function exportReport(recording, analysis) {
  const images = await Promise.all(CHART_DEFS.map(c => captureChart(c.id)))

  const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
  const pageW = 297
  const pageH = 210
  const margin = 15

  pdf.setFillColor(10, 10, 15)
  pdf.rect(0, 0, pageW, 24, 'F')
  pdf.setTextColor(233, 69, 96)
  pdf.setFontSize(18)
  pdf.setFont('helvetica', 'bold')
  pdf.text('Vedic Acoustica — Analysis Report', margin, 15)

  pdf.setTextColor(60, 60, 80)
  pdf.setFontSize(9)
  pdf.setFont('helvetica', 'normal')
  pdf.text(`Recording: ${recording.title}`, margin, pageH - 8)
  pdf.text(`Generated: ${new Date().toLocaleString()}`, pageW - margin, pageH - 8, { align: 'right' })

  let y = 31
  pdf.setTextColor(238, 238, 238)
  pdf.setFontSize(10)
  pdf.setFont('helvetica', 'bold')
  pdf.text('Summary', margin, y)
  y += 5.5
  pdf.setFont('helvetica', 'normal')
  pdf.setFontSize(9)
  const half = Math.ceil(summaryRows(analysis).length / 2)
  summaryRows(analysis).forEach(([label, value], i) => {
    const col = Math.floor(i / half)
    const row = i % half
    pdf.setTextColor(136, 136, 136)
    pdf.text(label, margin + col * 90, y + row * 5.5)
    pdf.setTextColor(238, 238, 238)
    pdf.text(String(value), margin + col * 90 + 45, y + row * 5.5)
  })

  const imgW = (pageW - margin * 2 - 8) / 2
  const imgH = imgW / 2.25

  // Running vertical position — advances per row and resets on page break
  let yPos = 57
  images.forEach((dataUrl, i) => {
    const col = i % 2
    const x   = margin + col * (imgW + 8)

    // Starting a new row (left column, not the first chart): advance yPos
    if (col === 0 && i > 0) yPos += imgH + 12

    // Page overflow: start a fresh page and reset to top margin
    if (yPos + imgH + 12 > pageH) {
      pdf.addPage('landscape', 'a4')
      yPos = 31
    }

    try {
      pdf.setFillColor(255, 255, 255)
      pdf.roundedRect(x, yPos, imgW, imgH, 3, 3, 'F')
      pdf.addImage(dataUrl, 'PNG', x + 3, yPos + 3, imgW - 6, imgH - 6)
    } catch (imgErr) {
      throw new Error(`Failed to embed "${CHART_DEFS[i].title}" image in the PDF: ${imgErr.message}`)
    }

    pdf.setTextColor(200, 200, 210)
    pdf.setFontSize(9)
    pdf.setFont('helvetica', 'bold')
    pdf.text(CHART_DEFS[i].title, x, yPos + imgH + 5)
  })

  pdf.save(`vedic-acoustica-report-${recording.id}.pdf`)
}