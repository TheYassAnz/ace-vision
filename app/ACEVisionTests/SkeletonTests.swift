import CoreGraphics
import Foundation
import Testing
@testable import ACEVision

struct SkeletonTests {
    @Test func poseDecodesNaNAsMissing() {
        var floats = [Float](repeating: 1.5, count: 2 * 17 * 2)
        floats[34] = .nan
        let pose = Pose(data: floats.withUnsafeBufferPointer { Data(buffer: $0) })
        #expect(pose.frames == 2)
        #expect(pose.point(frame: 1, joint: 0) == nil)
        #expect(pose.point(frame: 0, joint: 0) == CGPoint(x: 1.5, y: 1.5))
        #expect(pose.point(frame: 5, joint: 0) == nil)
    }

    @Test func fitRectLetterboxes() {
        #expect(Skeleton.fitRect(video: CGSize(width: 1920, height: 1080), in: CGSize(width: 800, height: 600)) == CGRect(x: 0, y: 75, width: 800, height: 450))
        let r = Skeleton.fitRect(video: CGSize(width: 1080, height: 1920), in: CGSize(width: 800, height: 600))
        #expect(r.width == 337.5 && r.minX == 231.25)
    }

    @Test func frameIndexIsClamped() {
        #expect(Skeleton.frame(at: 1.0, fps: 60, count: 100) == 60)
        #expect(Skeleton.frame(at: 5.0, fps: 60, count: 100) == 99)
        #expect(Skeleton.frame(at: -1, fps: 60, count: 100) == 0)
    }

    @Test func bonesAreValidJoints() {
        #expect(Skeleton.bones.count == 16)
        #expect(Skeleton.bones.allSatisfy { (0..<17).contains($0.0) && (0..<17).contains($0.1) })
    }
}
