import Foundation

/// RunWorkout을 Strava가 "정식 활동"으로 인식하는 TCX 문서로 변환.
///
/// GPS 좌표는 없지만(가민이 건강 앱에 경로를 안 남기므로) 시간·누적거리·심박수
/// 트랙포인트를 넣어 페이스/심박 그래프가 있는 활동으로 업로드됩니다. 지도만 없습니다.
enum TCXBuilder {

    private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    /// TCX XML 문자열을 만든다.
    static func makeTCX(from run: RunWorkout) -> String {
        let totalSeconds = max(run.duration, 1)
        let totalDistance = run.distanceMeters ?? 0
        let calories = Int((run.activeEnergyKcal ?? 0).rounded())

        let trackpoints = buildTrackpoints(run: run, totalSeconds: totalSeconds, totalDistance: totalDistance)

        var xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <TrainingCenterDatabase
          xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">
          <Activities>
            <Activity Sport="Running">
              <Id>\(iso.string(from: run.startDate))</Id>
              <Lap StartTime="\(iso.string(from: run.startDate))">
                <TotalTimeSeconds>\(String(format: "%.1f", totalSeconds))</TotalTimeSeconds>
                <DistanceMeters>\(String(format: "%.1f", totalDistance))</DistanceMeters>
                <Calories>\(calories)</Calories>
                <Intensity>Active</Intensity>
                <TriggerMethod>Manual</TriggerMethod>
                <Track>

        """

        for tp in trackpoints {
            xml += tp
        }

        xml += """
              </Track>
              </Lap>
              <Creator xsi:type="Device_t">
                <Name>NaraeSync</Name>
              </Creator>
            </Activity>
          </Activities>
        </TrainingCenterDatabase>
        """
        return xml
    }

    /// 트랙포인트 배열을 만든다.
    /// 심박수 샘플이 있으면 각 샘플 시각을 기준으로, 없으면 5초 간격으로 생성.
    /// 누적 거리는 경과 시간에 비례해 선형 보간.
    private static func buildTrackpoints(run: RunWorkout, totalSeconds: Double, totalDistance: Double) -> [String] {
        var points: [String] = []

        func distanceAt(elapsed: Double) -> Double {
            guard totalSeconds > 0 else { return 0 }
            let ratio = min(max(elapsed / totalSeconds, 0), 1)
            return totalDistance * ratio
        }

        func trackpoint(date: Date, distance: Double, bpm: Double?) -> String {
            var s = "          <Trackpoint>\n"
            s += "            <Time>\(iso.string(from: date))</Time>\n"
            s += "            <DistanceMeters>\(String(format: "%.1f", distance))</DistanceMeters>\n"
            if let bpm = bpm, bpm > 0 {
                s += "            <HeartRateBpm><Value>\(Int(bpm.rounded()))</Value></HeartRateBpm>\n"
            }
            s += "          </Trackpoint>\n"
            return s
        }

        if !run.heartRateSamples.isEmpty {
            for sample in run.heartRateSamples {
                let elapsed = sample.date.timeIntervalSince(run.startDate)
                guard elapsed >= 0 else { continue }
                points.append(trackpoint(date: sample.date, distance: distanceAt(elapsed: elapsed), bpm: sample.bpm))
            }
        }

        // 심박 샘플이 없거나 너무 적으면 시작/끝을 보장하기 위해 시간 간격 포인트를 넣는다.
        if points.count < 2 {
            points.removeAll()
            let step = 5.0
            var elapsed = 0.0
            while elapsed < totalSeconds {
                let date = run.startDate.addingTimeInterval(elapsed)
                points.append(trackpoint(date: date, distance: distanceAt(elapsed: elapsed), bpm: nil))
                elapsed += step
            }
            // 마지막 지점(정확한 총 거리/시간) 추가
            points.append(trackpoint(date: run.endDate, distance: totalDistance, bpm: nil))
        }

        return points
    }
}
