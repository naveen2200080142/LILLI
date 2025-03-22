import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:file_picker/file_picker.dart';

void main() => runApp(JarvisApp());

class JarvisApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JARVIS AI',
      theme: ThemeData.dark().copyWith(scaffoldBackgroundColor: Colors.black),
      home: JarvisChatScreen(),
    );
  }
}

class JarvisChatScreen extends StatefulWidget {
  @override
  _JarvisChatScreenState createState() => _JarvisChatScreenState();
}

class _JarvisChatScreenState extends State<JarvisChatScreen> with SingleTickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  List<String> messages = [];
  late AnimationController _holoController;
  bool isProcessing = false;

  @override
  void initState() {
    super.initState();
    _holoController = AnimationController(vsync: this, duration: Duration(seconds: 1));
    loadHistory();
  }

  @override
  void dispose() {
    _holoController.dispose();
    _controller.dispose();
    super.dispose();
  }

  Future<void> loadHistory() async {
    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:5000/api/history'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          messages = data['history'].map<String>((e) => "You: ${e['user_input']}\nJARVIS: ${e['assistant_response']}").toList();
        });
      }
    } catch (e) {
      print("History load error: $e");
    }
  }

  Future<void> sendMessage(String text, {bool isVoice = false, String? fileContent}) async {
    if (text.isEmpty && fileContent == null) return;
    setState(() {
      if (text.isNotEmpty) messages.add("You: $text");
      isProcessing = true;
      _holoController.repeat();
    });

    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:5000/api/message'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'message': text, 'isVoice': isVoice, 'file_content': fileContent ?? ''}),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          messages.add("JARVIS: ${data['response']}");
          isProcessing = false;
          _holoController.stop();
        });
      }
    } catch (e) {
      setState(() {
        messages.add("Error: $e");
        isProcessing = false;
        _holoController.stop();
      });
    }
    _controller.clear();
  }

  Future<void> uploadFile() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['txt']);
    if (result != null) {
      String fileContent = String.fromCharCodes(result.files.single.bytes!);
      sendMessage("", fileContent: fileContent);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Container(decoration: BoxDecoration(gradient: RadialGradient(center: Alignment.center, radius: 1.5, colors: [Colors.black, Colors.blueGrey.shade900]))),
          Center(
            child: AnimatedBuilder(
              animation: _holoController,
              builder: (context, child) => Opacity(
                opacity: isProcessing ? 1.0 : 0.3,
                child: Container(
                  width: 250,
                  height: 250,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(colors: [Colors.cyan.withOpacity(0.8 * _holoController.value), Colors.blue.withOpacity(0.3), Colors.transparent]),
                    boxShadow: [BoxShadow(color: Colors.cyanAccent.withOpacity(0.6), blurRadius: 40, spreadRadius: 15)],
                  ),
                  child: Center(child: Icon(Icons.auto_awesome, size: 100, color: Colors.cyanAccent)),
                ),
              ),
            ),
          ),
          Positioned(
            top: 50,
            left: 50,
            right: 50,
            bottom: 150,
            child: Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.black.withOpacity(0.7), borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.cyanAccent.withOpacity(0.5))),
              child: ListView.builder(
                itemCount: messages.length,
                itemBuilder: (context, index) => Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Text(messages[index], style: TextStyle(color: messages[index].startsWith("You:") ? Colors.white : Colors.cyanAccent, fontSize: 16)),
                ),
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Padding(
              padding: EdgeInsets.all(20),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: InputDecoration(
                        hintText: 'Ask JARVIS...',
                        hintStyle: TextStyle(color: Colors.cyanAccent.withOpacity(0.6)),
                        filled: true,
                        fillColor: Colors.black.withOpacity(0.8),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(30), borderSide: BorderSide(color: Colors.cyan)),
                      ),
                      style: TextStyle(color: Colors.white),
                      enabled: !isProcessing,
                    ),
                  ),
                  SizedBox(width: 10),
                  FloatingActionButton(onPressed: isProcessing ? null : () => sendMessage(_controller.text), child: Icon(Icons.send), backgroundColor: Colors.cyan),
                  SizedBox(width: 10),
                  FloatingActionButton(onPressed: isProcessing ? null : () => sendMessage("Listen", isVoice: true), child: Icon(Icons.mic), backgroundColor: Colors.cyan),
                  SizedBox(width: 10),
                  FloatingActionButton(onPressed: isProcessing ? null : uploadFile, child: Icon(Icons.attach_file), backgroundColor: Colors.cyan),
                ],
              ),
            ),
          ),
          if (isProcessing) Center(child: CircularProgressIndicator(color: Colors.cyanAccent)),
        ],
      ),
    );
  }
}