import SwiftUI

extension StrokeKind {
    var color: Color {
        switch self { case .forehand: .blue; case .backhand: .orange; case .serve: .green; case .other: .gray }
    }
}

/// Round forehand, square backhand, triangle serve, bar other: shape and colour both carry the kind.
struct KindShape: Shape {
    let kind: StrokeKind
    func path(in r: CGRect) -> Path {
        switch kind {
        case .forehand: return Path(ellipseIn: r)
        case .backhand: return Path(r)
        case .serve:
            var p = Path()
            p.move(to: CGPoint(x: r.midX, y: r.minY)); p.addLine(to: CGPoint(x: r.maxX, y: r.maxY)); p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
            p.closeSubpath()
            return p
        case .other: return Path(CGRect(x: r.midX - 1.5, y: r.minY - 2, width: 3, height: r.height + 4))
        }
    }
}

struct StrokeTimeline: View {
    let strokes: [Stroke]
    let notes: [Note]
    let duration: Double
    let model: PlayerModel
    @State private var cursor = 0.0
    @State private var hovered: Stroke?
    @FocusState private var focused: Bool
    private let size: CGFloat = 10

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Canvas { ctx, sz in
                for s in strokes {
                    let x = Timeline.x(s.t, duration: duration, width: sz.width)
                    let r = CGRect(x: x - size / 2, y: 18 - size / 2, width: size, height: size)
                    ctx.fill(KindShape(kind: s.kind).path(in: r), with: .color(s.kind.color))
                    if s.t == cursor && focused { ctx.stroke(Path(ellipseIn: r.insetBy(dx: -4, dy: -4)), with: .color(.primary), lineWidth: 1.5) }
                    if !s.defects.isEmpty { ctx.fill(Path(ellipseIn: CGRect(x: x - 3, y: 3, width: 6, height: 6)), with: .color(.red)) }
                }
                if !notes.isEmpty { ctx.draw(Text("Mes notes").font(.caption2).foregroundStyle(.secondary), at: CGPoint(x: 2, y: 36), anchor: .leading) }
                for n in notes {
                    let x = Timeline.x(n.t, duration: duration, width: sz.width)
                    ctx.fill(KindShape(kind: n.kind).path(in: CGRect(x: x - size / 2, y: 50 - size / 2, width: size, height: size)), with: .color(n.kind.color))
                }
                let px = Timeline.x(model.currentTime, duration: duration, width: sz.width)
                ctx.stroke(Path { $0.move(to: CGPoint(x: px, y: 0)); $0.addLine(to: CGPoint(x: px, y: sz.height)) }, with: .color(.primary), lineWidth: 1)
            }
            .frame(height: notes.isEmpty ? 30 : 60)  // the notes row only when there are notes
            .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 6))
            .overlay { GeometryReader { geo in Color.clear
                .contentShape(Rectangle())
                .onContinuousHover { phase in
                    if case .active(let p) = phase { hovered = nearest(x: p.x, width: geo.size.width) } else { hovered = nil }
                }
                .onTapGesture { p in
                    if let s = nearest(x: p.x, width: geo.size.width) { cursor = s.t }
                    model.seek(Timeline.x(p.x, duration: geo.size.width, width: duration) - 1.5)  // x⁻¹: pixels to seconds
                }
            } }
            .help(hovered.map(Timeline.label) ?? "")
            .focusable()
            .focused($focused)
            .onKeyPress(.leftArrow) { step(forward: false) }
            .onKeyPress(.rightArrow) { step(forward: true) }
            .onKeyPress(.return) { model.playClip(at: cursor); return .handled }
            .accessibilityChildren {
                ForEach(Array(strokes.enumerated()), id: \.offset) { _, s in
                    Rectangle().accessibilityLabel(Timeline.label(s))
                        .accessibilityAction(named: "Lire l'extrait") { model.playClip(at: s.t) }
                }
            }
            legend
        }
    }

    private var legend: some View {
        HStack(spacing: 12) {
            ForEach([StrokeKind.forehand, .backhand, .serve, .other], id: \.self) { k in
                HStack(spacing: 4) {
                    KindShape(kind: k).fill(k.color).frame(width: 10, height: 10)
                    Text(k.label)
                }
            }
            HStack(spacing: 4) { Circle().fill(.red).frame(width: 6, height: 6); Text("Défaut") }
        }
        .font(.caption).foregroundStyle(.secondary)
        .accessibilityHidden(true)
    }

    private func nearest(x: Double, width: Double) -> Stroke? {
        strokes.min { abs(Timeline.x($0.t, duration: duration, width: width) - x) < abs(Timeline.x($1.t, duration: duration, width: width) - x) }
            .flatMap { abs(Timeline.x($0.t, duration: duration, width: width) - x) <= 8 ? $0 : nil }
    }

    private func step(forward: Bool) -> KeyPress.Result {
        guard let s = Timeline.neighbor(of: cursor, in: strokes, forward: forward) else { return .handled }
        cursor = s.t
        model.seek(s.t - 1.5)
        return .handled
    }
}
