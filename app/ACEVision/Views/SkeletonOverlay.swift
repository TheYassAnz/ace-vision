import AVKit
import SwiftUI

/// The video player, with the player's skeleton drawn in AVPlayerView's content overlay (between the video and
/// the controls). A SwiftUI overlay is hidden behind the AppKit player view, and VideoPlayer's videoOverlay is
/// not redrawn when the skeleton is shown, hence AppKit here.
struct PlayerSurface: NSViewRepresentable {
    let player: AVPlayer
    let pose: Pose?
    let videoSize: CGSize
    let fps: Double

    func makeNSView(context: Context) -> AVPlayerView {
        let v = AVPlayerView()
        v.controlsStyle = .inline
        v.player = player
        let s = SkeletonView(frame: v.contentOverlayView?.bounds ?? .zero)
        s.autoresizingMask = [.width, .height]
        v.contentOverlayView?.addSubview(s)
        return v
    }

    func updateNSView(_ v: AVPlayerView, context: Context) {
        if v.player !== player { v.player = player }
        (v.contentOverlayView?.subviews.first as? SkeletonView)?.configure(pose: pose, videoSize: videoSize, fps: fps, player: player)
    }

    static func dismantleNSView(_ v: AVPlayerView, coordinator: ()) {
        (v.contentOverlayView?.subviews.first as? SkeletonView)?.configure(pose: nil, videoSize: .zero, fps: 0, player: nil)
    }
}

/// Draws the skeleton of the frame being shown. Purely visual: the timeline carries the information.
final class SkeletonView: NSView {
    private let outline = CAShapeLayer(), bones = CAShapeLayer()
    private var pose: Pose?, videoSize = CGSize.zero, fps = 0.0
    private weak var player: AVPlayer?
    private var observer: Any?

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        for (l, color, width) in [(outline, NSColor.black.withAlphaComponent(0.6), 5.0), (bones, NSColor.white, 3.0)] {
            l.strokeColor = color.cgColor
            l.fillColor = color.cgColor
            l.lineWidth = width
            l.lineCap = .round
            layer?.addSublayer(l)
        }
        setAccessibilityElement(false)
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    var drawnPath: CGPath? { bones.path }
    override var isFlipped: Bool { true }  // keypoints have y growing downward, like the video
    override func hitTest(_ point: NSPoint) -> NSView? { nil }  // clicks go to the player controls

    func configure(pose: Pose?, videoSize: CGSize, fps: Double, player: AVPlayer?) {
        self.pose = pose
        self.videoSize = videoSize
        self.fps = fps
        if player !== self.player || (pose == nil) != (observer == nil) {
            if let observer, let p = self.player { p.removeTimeObserver(observer) }
            observer = nil
            self.player = player
            if let player, pose != nil {
                // every 1/30 s while playing; AVPlayer also calls it on seeks and pauses
                observer = player.addPeriodicTimeObserver(forInterval: CMTime(value: 1, timescale: 30), queue: .main) { [weak self] t in
                    MainActor.assumeIsolated { self?.draw(at: t.seconds) }
                }
            }
        }
        draw(at: player?.currentTime().seconds ?? .nan)
    }

    override func layout() {
        super.layout()
        outline.frame = bounds
        bones.frame = bounds
        draw(at: player?.currentTime().seconds ?? .nan)
    }

    func draw(at t: Double) {
        let path = CGMutablePath()
        if let pose, pose.frames > 0, t.isFinite, fps > 0 {
            let f = Skeleton.frame(at: t, fps: fps, count: pose.frames)
            let r = Skeleton.fitRect(video: videoSize, in: bounds.size)
            let k = videoSize.width > 0 ? r.width / videoSize.width : 0
            func map(_ j: Int) -> CGPoint? { pose.point(frame: f, joint: j).map { CGPoint(x: r.minX + $0.x * k, y: r.minY + $0.y * k) } }
            for (a, b) in Skeleton.bones {
                if let p = map(a), let q = map(b) { path.move(to: p); path.addLine(to: q) }
            }
            for j in 0..<17 { if let p = map(j) { path.addEllipse(in: CGRect(x: p.x - 3, y: p.y - 3, width: 6, height: 6)) } }
        }
        CATransaction.begin()
        CATransaction.setDisableActions(true)  // no implicit fade between frames
        outline.path = path
        bones.path = path
        CATransaction.commit()
    }
    // the time observer is removed by configure(player: nil), called from PlayerSurface.dismantleNSView
}
