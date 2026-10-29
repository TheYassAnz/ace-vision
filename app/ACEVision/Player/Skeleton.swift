import CoreGraphics
import Foundation

/// Keypoints per video frame (COCO-17), as the engine sends them: Float32 little-endian, frame × joint × (x, y).
struct Pose: Sendable {
    private let values: [Float]
    let frames: Int

    init(data: Data) {
        values = data.withUnsafeBytes { raw in
            (0..<raw.count / 4).map { Float(bitPattern: UInt32(littleEndian: raw.loadUnaligned(fromByteOffset: $0 * 4, as: UInt32.self))) }
        }
        frames = values.count / 34
    }

    func point(frame: Int, joint: Int) -> CGPoint? {
        guard (0..<frames).contains(frame), (0..<17).contains(joint) else { return nil }
        let i = (frame * 17 + joint) * 2
        let x = values[i], y = values[i + 1]
        return x.isNaN || y.isNaN ? nil : CGPoint(x: CGFloat(x), y: CGFloat(y))
    }
}

enum Skeleton {
    static let bones: [(Int, Int)] = [
        (0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    ]

    /// Where the player draws the video: aspect fit, centered.
    static func fitRect(video: CGSize, in container: CGSize) -> CGRect {
        guard video.width > 0, video.height > 0 else { return .zero }
        let s = min(container.width / video.width, container.height / video.height)
        let size = CGSize(width: video.width * s, height: video.height * s)
        return CGRect(x: (container.width - size.width) / 2, y: (container.height - size.height) / 2, width: size.width, height: size.height)
    }

    static func frame(at t: Double, fps: Double, count: Int) -> Int {
        max(0, min(count - 1, Int(t * fps)))
    }
}
