import Foundation
import HealthKit

/// HealthKit에서 달리기 기록과 심박수를 읽는 담당.
final class HealthKitManager {
    static let shared = HealthKitManager()

    let store = HKHealthStore()

    private init() {}

    var isHealthDataAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    /// 읽기 권한 요청 대상 타입들.
    private var readTypes: Set<HKObjectType> {
        var types: Set<HKObjectType> = [HKObjectType.workoutType()]
        if let hr = HKObjectType.quantityType(forIdentifier: .heartRate) {
            types.insert(hr)
        }
        if let dist = HKObjectType.quantityType(forIdentifier: .distanceWalkingRunning) {
            types.insert(dist)
        }
        if let energy = HKObjectType.quantityType(forIdentifier: .activeEnergyBurned) {
            types.insert(energy)
        }
        return types
    }

    /// 건강 데이터 읽기 권한 요청.
    func requestAuthorization() async throws {
        guard isHealthDataAvailable else {
            throw NaraeError.healthDataUnavailable
        }
        try await store.requestAuthorization(toShare: [], read: readTypes)
    }

    /// 최근 `days`일 이내의 달리기 기록을 최신순으로 반환.
    /// `garminOnly`가 true면 출처 앱 이름에 "garmin"이 포함된 것만 반환(중복 방지).
    func fetchRuns(days: Int = 60, garminOnly: Bool = true) async throws -> [RunWorkout] {
        let workoutType = HKObjectType.workoutType()
        let start = Calendar.current.date(byAdding: .day, value: -days, to: Date()) ?? Date.distantPast

        let datePredicate = HKQuery.predicateForSamples(withStart: start, end: Date(), options: [])
        let runningPredicate = HKQuery.predicateForWorkouts(with: .running)
        let predicate = NSCompoundPredicate(andPredicateWithSubpredicates: [datePredicate, runningPredicate])
        let sort = NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)

        let workouts: [HKWorkout] = try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: workoutType,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: [sort]
            ) { _, samples, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: (samples as? [HKWorkout]) ?? [])
            }
            store.execute(query)
        }

        var results: [RunWorkout] = []
        for workout in workouts {
            let sourceName = workout.sourceRevision.source.name
            if garminOnly && !sourceName.lowercased().contains("garmin") {
                continue
            }

            let distance = workout.totalDistance?.doubleValue(for: .meter())
            let energy = workout.totalEnergyBurned?.doubleValue(for: .kilocalorie())
            let hrSamples = try await fetchHeartRate(for: workout)

            results.append(
                RunWorkout(
                    id: workout.uuid,
                    startDate: workout.startDate,
                    endDate: workout.endDate,
                    distanceMeters: distance,
                    duration: workout.duration,
                    activeEnergyKcal: energy,
                    sourceName: sourceName,
                    heartRateSamples: hrSamples
                )
            )
        }
        return results
    }

    /// 특정 운동 구간의 심박수 샘플을 시간순으로 반환.
    private func fetchHeartRate(for workout: HKWorkout) async throws -> [HeartRateSample] {
        guard let hrType = HKObjectType.quantityType(forIdentifier: .heartRate) else {
            return []
        }
        let predicate = HKQuery.predicateForObjects(from: workout)
        let sort = NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)
        let unit = HKUnit.count().unitDivided(by: .minute())

        let samples: [HKQuantitySample] = try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: hrType,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: [sort]
            ) { _, samples, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: (samples as? [HKQuantitySample]) ?? [])
            }
            store.execute(query)
        }

        return samples.map {
            HeartRateSample(date: $0.startDate, bpm: $0.quantity.doubleValue(for: unit))
        }
    }
}
