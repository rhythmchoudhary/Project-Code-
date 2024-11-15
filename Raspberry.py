#include <Wire.h>
#include <HX711.h>
#include <WiFiNINA.h>
#include <ArduinoMqttClient.h>
#include <EMailSender.h>

// WiFi credentials
const char* ssid = "RHYTHM-victus";
const char* password = "mikul543";
const char* emailpass = "xoxb whgk owre aakl";

// Email sender setup
EMailSender emailSend("rhythmembeddedsystem@gmail.com", emailpass);

// MQTT settings
const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* topic_weight = "device/weight";
const char* topic_pulse = "device/pulse";
const char* topic_temperature = "device/temperature";

// HX711 setup for weight
#define LOADCELL_DOUT_PIN 4
#define LOADCELL_SCK_PIN 5
HX711 scale;

// Pulse sensor setup
const int PULSE_SENSOR_PIN = A0;
int Signal;
int Threshold = 550;

// LM35 temperature sensor setup
#define sensorPin A1

// WiFi and MQTT client objects
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

void setup() {
  Serial.begin(115200);

  // Initialize WiFi and MQTT
  connectWiFi();
  connectMQTT();

  // Initialize HX711 for weight measurement
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.set_offset(4294798238); // Updated offset
  scale.set_scale(593.024292);  // Updated scale factor
  Serial.println("Scale initialized with new calibration values.");

  // Initialize pin for pulse sensor
  pinMode(LED_BUILTIN, OUTPUT);
}

void connectWiFi() {
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
}

void connectMQTT() {
  Serial.print("Connecting to MQTT broker...");
  while (!mqttClient.connect(mqtt_broker, mqtt_port)) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to MQTT broker");
}

void sendEmail(String subject, String body) {
  EMailSender::EMailMessage message;
  message.subject = subject;
  message.message = body;

  // Check WiFi connection before sending
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Reconnecting to WiFi...");
    connectWiFi();
  }

  Serial.println("Attempting to send email...");
  EMailSender::Response resp = emailSend.send("neonatehealthmonitoringsystem@gmail.com", message);
  
  // Print the response status to debug
  Serial.print("Email send status code: ");
  Serial.println(resp.code);
  Serial.print("Email send description: ");
  Serial.println(resp.desc);

  // Fix the comparison to match String data type
  if (String(resp.code) != "1") { // Now treating resp.code as a String
    Serial.println("Failed to send email. Check your credentials and WiFi connection.");
  } else {
    Serial.println("Email sent successfully!");
  }
}


void loop() {
  // Poll the MQTT client to maintain connection
  mqttClient.poll();

  // Get weight data
  float weight = scale.get_units(20); // Average 20 readings
  if (weight < 0) {
    weight = 0; // Ensure no negative weights are reported
  }

  // Publish weight data
  char message_weight[50];
  snprintf(message_weight, sizeof(message_weight), "Weight: %.2f g", weight);
  mqttClient.beginMessage(topic_weight);
  mqttClient.print(message_weight);
  mqttClient.endMessage();
  Serial.print("Publishing weight: ");
  Serial.println(message_weight);

  // Get pulse sensor data
  Signal = analogRead(PULSE_SENSOR_PIN);
  if (Signal > Threshold) {
    digitalWrite(LED_BUILTIN, HIGH); // LED indicates heartbeat
  } else {
    digitalWrite(LED_BUILTIN, LOW);
  }
  char message_pulse[50];
  snprintf(message_pulse, sizeof(message_pulse), "Pulse Signal: %d", Signal);
  mqttClient.beginMessage(topic_pulse);
  mqttClient.print(message_pulse);
  mqttClient.endMessage();
  Serial.print("Publishing pulse: ");
  Serial.println(message_pulse);

  // Check for abnormal heart rate values
  if (Signal > 60 || Signal < 100) {
    String subject = "Heart Rate Alert";
    String body = "Abnormal heart rate detected.\nPulse Signal: " + String(Signal);
    sendEmail(subject, body);
  }

  // Get temperature data
  int reading = analogRead(sensorPin);
  float voltage = reading * (5.0 / 1024.0);
  float temperatureC = voltage * 100;
  char message_temperature[50];
  snprintf(message_temperature, sizeof(message_temperature), "Temperature: %.2f C", temperatureC);
  mqttClient.beginMessage(topic_temperature);
  mqttClient.print(message_temperature);
  mqttClient.endMessage();
  Serial.print("Publishing temperature: ");
  Serial.println(message_temperature);

  // Check for abnormal temperature values
  if (temperatureC > 36.1 || temperatureC < 37.2) {
    String subject = "Temperature Alert";
    String body = "Abnormal temperature detected.\nTemperature: " + String(temperatureC, 2) + "°C";
    sendEmail(subject, body);
  }

  delay(5000); // Delay between transmissions
}
