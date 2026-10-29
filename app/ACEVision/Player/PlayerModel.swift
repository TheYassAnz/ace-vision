import AVFoundation
import Observation

/// Numbers clip requests so a late seek completion from an older request can be recognised and dropped.
struct ClipGeneration {
    private var current = 0
    mutating func next() -> Int { current += 1; return current }
    func isCurrent(_ g: Int) -> Bool { g == current }
}

@MainActor @Observable
final class PlayerModel {
    let player: AVPlayer
    private(set) var currentTime = 0.0
    @ObservationIgnored nonisolated(unsafe) private var periodic: Any?
    @ObservationIgnored nonisolated(unsafe) private var boundary: Any?
    @ObservationIgnored private var generation = ClipGeneration()
    @ObservationIgnored nonisolated(unsafe) private var status: NSKeyValueObservation?

    init(url: URL) {
        player = AVPlayer(url: url)
        periodic = player.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.1, preferredTimescale: 600), queue: .main) { [weak self] t in
            Task { @MainActor in self?.currentTime = t.seconds }
        }
        // a manual pause cancels the planned clip stop
        status = player.observe(\.timeControlStatus) { [weak self] p, _ in
            guard p.timeControlStatus == .paused else { return }
            Task { @MainActor in self?.clearBoundary() }
        }
    }

    deinit {
        if let periodic { player.removeTimeObserver(periodic) }
        if let boundary { player.removeTimeObserver(boundary) }
    }

    func seek(_ t: Double) {
        currentTime = max(0, t)
        player.seek(to: CMTime(seconds: max(0, t), preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero)
    }

    func togglePlay() { player.timeControlStatus == .paused ? player.play() : player.pause() }

    func playClip(at t: Double) {
        let clip = Timeline.clip(t)
        clearBoundary()
        let g = generation.next()
        let start = CMTime(seconds: clip.lowerBound, preferredTimescale: 600)
        currentTime = clip.lowerBound
        player.seek(to: start, toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] finished in
            Task { @MainActor in
                guard let self, finished, self.generation.isCurrent(g) else { return }
                self.clearBoundary()
                self.player.play()
                self.boundary = self.player.addBoundaryTimeObserver(forTimes: [NSValue(time: CMTime(seconds: clip.upperBound, preferredTimescale: 600))], queue: .main) { [weak self] in
                    Task { @MainActor in self?.player.pause() }
                }
            }
        }
    }

    private func clearBoundary() {
        if let boundary { player.removeTimeObserver(boundary); self.boundary = nil }
    }
}
