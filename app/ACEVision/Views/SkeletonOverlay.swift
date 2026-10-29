import AVFoundation
import SwiftUI

/// Draws the player's skeleton on the video frame being shown. Purely visual: the timeline carries the information.
struct SkeletonOverlay: View {
    let pose: Pose
    let videoSize: CGSize
    let fps: Double
    let player: AVPlayer

    var body: some View {
        TimelineView(.animation) { _ in
            Canvas { ctx, size in
                let t = player.currentTime().seconds
                guard t.isFinite, pose.frames > 0 else { return }
                let f = Skeleton.frame(at: t, fps: fps, count: pose.frames)
                let r = Skeleton.fitRect(video: videoSize, in: size)
                let k = r.width / videoSize.width
                func map(_ j: Int) -> CGPoint? { pose.point(frame: f, joint: j).map { CGPoint(x: r.minX + $0.x * k, y: r.minY + $0.y * k) } }
                var bones = Path(), joints = Path()
                for (a, b) in Skeleton.bones {
                    if let p = map(a), let q = map(b) { bones.move(to: p); bones.addLine(to: q) }
                }
                for j in 0..<17 { if let p = map(j) { joints.addEllipse(in: CGRect(x: p.x - 4, y: p.y - 4, width: 8, height: 8)) } }
                ctx.stroke(bones, with: .color(.black.opacity(0.6)), lineWidth: 5)  // dark outline first: readable on light and dark courts
                ctx.stroke(joints, with: .color(.black.opacity(0.6)), lineWidth: 2)
                ctx.stroke(bones, with: .color(.white), lineWidth: 3)
                ctx.fill(joints, with: .color(.white))
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
