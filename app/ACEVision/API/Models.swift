import Foundation

enum StrokeKind: String, Codable, Sendable, Hashable { case forehand, backhand, serve, other }
enum CourtView: String, Codable, Sendable, Hashable { case net, rear }  // not `View`: SwiftUI owns it
enum MatchStatus: String, Codable, Sendable, Hashable { case pending, running, done, failed }
enum DefectId: String, Codable, Sendable, Hashable {
    case latePrep = "late_prep", smallTurn = "small_turn", straightLegs = "straight_legs", narrowStance = "narrow_stance"
}
enum Outcome: String, Codable, Sendable, Hashable { case net, long, wide, `in`, unknown }
enum RallyEnd: String, Codable, Sendable, Hashable {
    case net, long, wide, notReturned = "not_returned", unknown
}
enum Handedness: String, Codable, Sendable, Hashable { case right, left }

struct Stroke: Codable, Sendable, Hashable {
    let t: Double
    let frame: Int
    let kind: StrokeKind
    let defects: [DefectId]
    let outcome: Outcome
    var wristSpeed: Double? = nil  // torso lengths / s; nil on matches analysed before it existed. var: optional in the memberwise init
}

struct Rally: Codable, Sendable, Hashable {
    let startT: Double
    let endT: Double
    let nHits: Int
    let end: RallyEnd
    let lastStroke: StrokeKind?
    let userHitLast: Bool
    let isServeFault: Bool
}

struct Finding: Codable, Sendable, Hashable {
    let kind: StrokeKind
    let defect: DefectId
    let count: Int
    let total: Int
    let title: String
    let text: String
    let drill: String
    let clipTimes: [Double]
}

struct Score: Codable, Sendable, Hashable {
    let nNotes: Int
    let nDetected: Int
    let foundRate: Double
    let classRate: Double
    let falseHits: Int
}

struct VideoInfo: Codable, Sendable, Hashable {
    let width: Int
    let height: Int
    let fps: Double
    let durationS: Double
    let nFrames: Int
    let rotation: Int
    let created: String?
}

struct Settings: Codable, Sendable, Hashable {
    var handedness: Handedness
    var backhandHands: Int
}

struct Match: Codable, Sendable, Hashable {
    let id: String
    let title: String
    let view: CourtView
    let status: MatchStatus
    let progress: Double
    let error: String?
    let videoFile: String
    let info: VideoInfo?
    let settings: Settings
    let strokes: [Stroke]
    let rallies: [Rally]?
    let findings: [Finding]
    let score: Score?
    let coverage: Double?
    let nUnmeasured: Int
}

struct DefectRate: Codable, Sendable, Hashable {
    let kind: StrokeKind
    let defect: DefectId
    let rate: Double
}

struct MatchSummary: Codable, Sendable, Hashable, Identifiable {
    let id: String
    let title: String
    let view: CourtView
    let status: MatchStatus
    let progress: Double
    let error: String?
    let created: String?
    let durationS: Double?
    let score: Score?
    let defectRates: [DefectRate]
}

struct Note: Codable, Sendable, Hashable {
    var t: Double
    var kind: StrokeKind
}

struct ImportResult: Codable, Sendable, Hashable {
    let match: MatchSummary
    let queued: Bool
}

extension JSONDecoder {
    static var ace: JSONDecoder {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }
}

extension JSONEncoder {
    static var ace: JSONEncoder {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }
}
