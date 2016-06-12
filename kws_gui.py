#!/usr/bin/env python3

from tkinter import *
from tkinter import ttk
from tkinter import filedialog, messagebox

import os
from json import loads as j_loads
from json import load as j_load

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)


class CustomText(Text):
    def __init__(self, *args, **kwargs):
        Text.__init__(self, *args, **kwargs)

    def highlight_pattern(self, pattern, tag, start="1.0", end="end",
                          regexp=False):
        start = self.index(start)
        end = self.index(end)
        self.mark_set("matchStart", start)
        self.mark_set("matchEnd", start)
        self.mark_set("searchLimit", end)

        count = IntVar()
        while True:
            index = self.search(pattern, "matchEnd","searchLimit",
                                count=count, regexp=regexp)
            if index == "": break
            if count.get() == 0: break
            self.mark_set("matchStart", index)
            self.mark_set("matchEnd", "%s+%sc" % (index, count.get()))
            self.tag_add(tag, "matchStart", "matchEnd")


class Kws:
    def __init__(self, master):
        self.master = master

        self.audio_fn_sv = StringVar()
        self.audio_descr_fn_sv = StringVar()
        self.detection_rate_sv = StringVar()
        self.faulty_alarm_sv = StringVar()
        self.counter_sv = StringVar()

        self._general()
        self._style()
        self._create_lframe_kws().grid(row=0, column=0, sticky=(N, S, E, W))
        self._create_lframe_add_audio_file().grid(row=1, column=0, sticky=(N, S, E, W))
        self._create_lframe_quality().grid(row=2, column=0, sticky=(N, S, E, W))

        fr_text_widget = Frame(master=self.master)
        scrollbar = Scrollbar(master=fr_text_widget)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.text_widget = CustomText(master=fr_text_widget, state=DISABLED, height=7)
        self.text_widget.tag_configure("red", foreground="#ff0000")
        self.text_widget.pack()

        self.text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_widget.yview)
        fr_text_widget.grid(row=3, column=0, sticky=(N, S, E, W))
        self.flagtext = True
        self._reset_variables()
        self._init_gst(online=True)
        self._init_gst(online=False)

    # ---START: GUI methods---
    def _reset_variables(self):
        self.audio_fn = None
        self.audio_fn_sv.set("Undefined")

        self.audio_descr_fn = None
        self.audio_descr_fn_sv.set("Undefined")

        self.btn_add_audio_descr.config(state=DISABLED)
        self._reset_session_variables()

    def _reset_session_variables(self):
        """Do it on each pressing of "start" button"""
        self.timestamps = []
        self.counter_sv.set("Counter: n/a")
        self.detection_rate_sv.set("n/a")
        self.faulty_alarm_sv.set("n/a")

        self.text_widget.config(state=NORMAL)
        self.text_widget.delete("1.0", END)
        self.text_widget.config(state=DISABLED)
        self.flagtext = True
        for i in self.treeview.get_children():
            self.treeview.delete(i)

    @staticmethod
    def _style():
        style = ttk.Style()
        style.configure(style="TEntry", padding=3)
        style.configure(style="TLabel", padding=5, background='#333333', foreground='#FFFFFF')
        style.configure(style="TLabelframe", padding=5, background='#333333', foreground='#FFFFFF')
        style.configure(style="TLabelframe.Label", padding=5, background='#333333', foreground='#FFFFFF')
        style.configure(style="TButton", background='#FF8833', foreground='#000000')
        style.map(style="TButton", background=[('disabled', '#777777'),
                                               ('pressed', '#FFEE33'),
                                               ('active', '#FFAA33')])

    def _general(self):
        self.master.geometry("+100+100")
        self.master.resizable(FALSE, FALSE)
        self.master.config(width=300, background='#333333', padx=5, pady=5)
        self.master.title("KWS 2in1")

    def _create_lframe_kws(self):
        lfr_kws = ttk.LabelFrame(master=self.master, text="Key-word search")

        ttk.Label(master=lfr_kws, text="Key-word/key-phrase").grid(row=0, column=0, sticky=(N, S, E, W))
        self.entry_kw = ttk.Entry(master=lfr_kws)

        self.btn_start = ttk.Button(master=lfr_kws, text="Start", command=self._start)
        self.btn_start.grid(row=2, column=0, sticky=(N, S, E, W), pady=3)

        btn_reset = ttk.Button(master=lfr_kws, text="Reset", command=self._reset_variables)
        btn_reset.grid(row=3, column=0, sticky=(N, S, E, W), pady=3)

        fr_timestamps = ttk.Frame(master=lfr_kws)
        scrollbar = Scrollbar(master=fr_timestamps)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.treeview = ttk.Treeview(master=fr_timestamps, height=3)
        self.treeview.heading('#0', text="Timestamp")
        self.treeview.pack()

        self.treeview.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.treeview.yview)

        self.entry_kw.grid(row=1, column=0, sticky=(N, S, E, W))
        fr_timestamps.grid(row=0, column=1, sticky=(N, S, E, W), rowspan=3, padx=5)

        ttk.Label(master=lfr_kws, textvariable=self.counter_sv).grid(row=3, column=1, sticky=(N, S, E, W))
        return lfr_kws

    def _start(self):
        if self.btn_start.cget("text") == "Start":
            # Read keyword with converting it into UPPER case (current model provides recognized text in upper case)
            self.keyword = self.entry_kw.get().upper()
            #FIXME: add kw verification using regex
            if not self.keyword or self.keyword.strip() == "":
                messagebox.showerror("KWS ERROR", "Keyword is not defined")
                return
            self._reset_session_variables()
            if self.audio_fn:
                self.filesrc.set_property('location', self.audio_fn)
                self.pipeline_test.set_state(Gst.State.PLAYING)
            else:
                self.pipeline_online.set_state(Gst.State.PLAYING)
            self.counter_sv.set("Counter: 0")
            self.btn_start.config(text="Stop")
        else:
            self.btn_start.config(text="Start")
            self.pipeline_online.set_state(Gst.State.PAUSED)
            self.pipeline_test.set_state(Gst.State.NULL)

    def _create_lframe_add_audio_file(self):
        lfr_audio_file = ttk.LabelFrame(master=self.master, text="Add audio")

        btn_add_audio = ttk.Button(master=lfr_audio_file, text="Add audio file", command=self._cmd_add_audio)
        btn_add_audio.grid(row=0, column=0, sticky=(N, S, E, W))
        ttk.Label(master=lfr_audio_file, textvariable=self.audio_fn_sv).grid(row=0, column=1, sticky=(N, S, E, W))

        self.btn_add_audio_descr = ttk.Button(master=lfr_audio_file,
                                              text="Add audio file descriptor",
                                              command=self._cmd_add_audio_descr,
                                              state=DISABLED)
        self.btn_add_audio_descr.grid(row=1, column=0, sticky=(N, S, E, W))
        ttk.Label(master=lfr_audio_file, textvariable=self.audio_descr_fn_sv).grid(row=1, column=1, sticky=(N, S, E, W))

        return lfr_audio_file

    def _create_lframe_quality(self):
        lfr_quality = ttk.LabelFrame(master=self.master, text="Quality of KWS")
        ttk.Label(master=lfr_quality, text="Detection rate:").grid(row=0, column=0, sticky=(N, S, E, W))
        ttk.Label(master=lfr_quality, text="Faulty alarm:").grid(row=1, column=0, sticky=(N, S, E, W))
        ttk.Label(master=lfr_quality, textvariable=self.detection_rate_sv).grid(row=0, column=1, sticky=(N, S, E, W))
        ttk.Label(master=lfr_quality, textvariable=self.faulty_alarm_sv).grid(row=1, column=1, sticky=(N, S, E, W))
        return lfr_quality

    def _cmd_add_audio(self):
        audio_fn = filedialog.askopenfilename(parent=self.master,
                                              title="Choose audio file for KWS",
                                              filetypes=[("Audio files", "*.wav *.mp3")])
        if audio_fn:
            self._reset_variables()
            self.audio_fn = audio_fn
            self.audio_fn_sv.set(os.path.split(audio_fn)[-1])
            self.btn_add_audio_descr.config(state=NORMAL)

    def _cmd_add_audio_descr(self):
        self.audio_descr_fn = filedialog.askopenfilename(parent=self.master,
                                                         title="Choose description of audio file",
                                                         initialfile=os.path.splitext(self.audio_fn)[0] + ".json",
                                                         filetypes=[("Audio descriptor", ".json")])
        if self.audio_descr_fn:
            self.audio_descr_fn_sv.set(os.path.split(self.audio_descr_fn)[-1])

    def _display_found_timestamps(self, timestamps):
        for ts in timestamps:
            print(ts)
            item = self.treeview.insert('', 'end', len(self.treeview.get_children()), text=ts)
            self.treeview.selection_set(item)
            self.treeview.see(item)

        self.counter_sv.set("Counter: {0}".format(len(self.timestamps)))
    # ---END: GUI methods---

    def _init_gst(self, online=False):
        def on_pad_added(_, pad):
            pad.link(self.audioconvert.get_static_pad('sink'))

        if online:
            pulsesrc = Gst.ElementFactory.make("pulsesrc", "pulsesrc")
            audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")
        else:
            decode = Gst.ElementFactory.make("decodebin", 'decode')
            decode.connect('pad-added', on_pad_added)
            self.filesrc = Gst.ElementFactory.make('filesrc', 'filesrc')
            self.audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")

        audioresample = Gst.ElementFactory.make("audioresample", "audioresample")
        asr = Gst.ElementFactory.make("kaldinnet2onlinedecoder", "asr")
        fakesink = Gst.ElementFactory.make("fakesink", "fakesink")

        asr.set_property("fst", "HCLG.fst")
        asr.set_property("model", "final.mdl")
        asr.set_property("word-syms", "words.txt")
        asr.set_property("phone-syms", "phones.txt")
        asr.set_property("word-boundary-file", "phones/word_boundary.int")
        asr.set_property("feature-type", "mfcc")
        asr.set_property("mfcc-config", "conf/mfcc.conf")
        asr.set_property("ivector-extraction-config", "conf/ivector_extractor.fixed.conf")
        asr.set_property("max-active", 7000)
        asr.set_property("beam", 10.0)
        asr.set_property("lattice-beam", 6.0)
        asr.set_property("do-endpointing", True)
        asr.set_property("do-phone-alignment", True)
        asr.set_property("num-nbest", 1)
        asr.set_property("endpoint-silence-phones", "1:2:3:4:5:6:7:8:9:10")
        asr.set_property("use-threaded-decoder", False)
        asr.set_property("chunk-length-in-secs", 0.2)
        asr.set_property("silent", False)

        if online:
            self.pipeline_online = Gst.Pipeline()
            for element in [pulsesrc, audioconvert, audioresample, asr, fakesink]:
                self.pipeline_online.add(element)
        else:
            self.pipeline_test = Gst.Pipeline()
            for element in [self.filesrc, decode, self.audioconvert, audioresample, asr, fakesink]:
                self.pipeline_test.add(element)

        if online:
            pulsesrc.link(audioconvert)
            audioconvert.link(audioresample)
        else:
            self.filesrc.link(decode)
            self.audioconvert.link(audioresample)

        audioresample.link(asr)
        asr.link(fakesink)

        asr.connect('full-final-result', self._handle_full_final_result)
        asr.connect('end-of-audio', self._handle_end_of_audio)

        if online:
            self.pipeline_online.set_state(Gst.State.NULL)
        else:
            self.pipeline_test.set_state(Gst.State.NULL)

    # ---START: KWS methods---
    def _handle_full_final_result(self, _, json_str):
        keyword = self.keyword
        json_data = j_loads(json_str)
        result = []
        kw_list = keyword.split(" ") # represents the phrase splitted on words
        word_alignment = json_data["result"]["hypotheses"][0]["word-alignment"]

        # summing the time stamp of a word with segment-start time
        for i in word_alignment:
            i["start"] += json_data["segment-start"]
        # making search of any occurances of the keyword
        for i, j in enumerate(word_alignment):
            # in case come across the first element in kw_list
            if j["word"] == kw_list[0]:
                kw_list_length = len(kw_list)
                slice = word_alignment[i: i + kw_list_length]
                # if the amount of words in the phrase equal to 1
                # then save the slice and continue looping
                flag = True
                if kw_list_length != 1:
                    # else we check whether all sequential elements in slice
                    # equal to words in phrase or not
                    iter = 0
                    for item in kw_list:
                        if iter == len(slice):
                            flag = False
                            break
                        if item == slice[iter]["word"] and iter != 0:
                            pass
                        elif iter != 0 and item != slice[iter]["word"]:
                            flag = False
                        iter += 1
                if flag is True:
                    print(slice)
                    result.append(slice[0]["start"])

        self.timestamps.extend(result)

        self._display_found_timestamps(result)

        self.text_widget.config(state=NORMAL)
        if self.flagtext is True:
            self.text_widget.insert("end -1 chars", " {0} ".format(json_data["result"]["hypotheses"][0]["transcript"]))
            self.flagtext = False
        else:
            self.text_widget.insert("end -1 chars", "{0} ".format(json_data["result"]["hypotheses"][0]["transcript"]))
        self.text_widget.highlight_pattern(" {0} ".format(self.keyword), "red")
        self.text_widget.see(END)
        self.text_widget.config(state=DISABLED)

    def _handle_end_of_audio(self, _, __):
        self.pipeline_test.set_state(Gst.State.NULL)
        self.btn_start.config(text="Start")
        if not self.audio_descr_fn:
            return
        keyword = self.keyword

        result = self.timestamps
        audio_file_descriptor_json = j_load(open(self.audio_descr_fn))
        num_of_words = audio_file_descriptor_json["num-of-words"]
        if num_of_words <= 0:
            return

        if keyword not in audio_file_descriptor_json:
            messagebox.showwarning("KWS warning", "Keyword \"{0}\" was not found in the selected descriptor.\n"
                                                  "Quality of KWS can't be measured".format(keyword))
            return
        #####################################################
        #       num_of_truly_detected_keywords              #
        # DR = ------------------------------- * 100 %      #
        #       num_of_real_keywords                        #
        #####################################################

        #####################################################
        #       num_of_false_detected_keywords              #
        # FA = ------------------------------------ * 100 % #
        #      num_of_words - num_of_real_keywords          #
        #####################################################

        num_of_real_keywords = len(audio_file_descriptor_json[keyword])
        real_keywords_list = audio_file_descriptor_json[keyword]

        truly_detected = []
        false_detected = []
        undetected = list(real_keywords_list) # a copy of real_keywords_list
        for i in range(0, len(result)):
            val = round(result[i])
            try:
                undetected.index(val)
                undetected.remove(val)
                truly_detected.append(val)
            except ValueError:
                false_detected.append(val)
        # all necessary vars
        print(truly_detected, false_detected, undetected)
        num_of_truly_detected_keywords = len(truly_detected)
        num_of_false_detected_keywords = len(false_detected)

        DR = (float(num_of_truly_detected_keywords) / num_of_real_keywords) * 100
        DR_str = '%.2f' % DR

        FA = (float(num_of_false_detected_keywords) / (num_of_words - num_of_real_keywords)) * 100
        FA_str = '%.2f' % FA

        self.detection_rate_sv.set("{0} %".format(DR_str))
        self.faulty_alarm_sv.set("{0} %".format(FA_str))

    # ---END: KWS methods---

if __name__ == "__main__":
    root = Tk()
    main_window = Kws(root)
    root.mainloop()
