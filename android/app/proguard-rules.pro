# WorkManager's database is created by reflection through its no-argument constructor, and
# the libraries keep the class but not the constructor. Without this the app crashes on launch.
-keepclassmembers class * extends androidx.room.RoomDatabase {
    <init>();
}
