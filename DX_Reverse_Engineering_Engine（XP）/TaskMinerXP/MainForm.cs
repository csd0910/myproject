using System;
using System.Drawing;
using System.Windows.Forms;
using System.IO;

namespace TaskMinerXP
{
    public class MainForm : Form
    {
        private TaskMinerManager _manager;
        private Button _btnToggle;
        private TextBox _txtLogDir;
        private Label _lblStatus;
        private bool _isRecording = false;

        public MainForm()
        {
            this.Text = "DX推進アシスタント (AIロガー - XP版)";
            this.Size = new Size(400, 250);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;

            InitializeUI();
            this.FormClosing += MainForm_FormClosing;
        }

        private void InitializeUI()
        {
            Label lblDir = new Label() { Text = "【ログ保存フォルダ】", Location = new Point(15, 15), AutoSize = true };
            this.Controls.Add(lblDir);

            _txtLogDir = new TextBox() { Location = new Point(15, 35), Width = 280 };
            _txtLogDir.Text = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "activity_logs");
            this.Controls.Add(_txtLogDir);

            Button btnBrowse = new Button() { Text = "参照", Location = new Point(300, 33), Width = 60 };
            btnBrowse.Click += BtnBrowse_Click;
            this.Controls.Add(btnBrowse);

            _btnToggle = new Button() { Text = "記録開始", Location = new Point(15, 80), Size = new Size(345, 60), Font = new Font("MS UI Gothic", 16, FontStyle.Bold), ForeColor = Color.Red };
            _btnToggle.Click += BtnToggle_Click;
            this.Controls.Add(_btnToggle);

            _lblStatus = new Label() { Text = "状態: 待機中...", Location = new Point(15, 160), AutoSize = true };
            this.Controls.Add(_lblStatus);
        }

        private void BtnBrowse_Click(object sender, EventArgs e)
        {
            using (FolderBrowserDialog dlg = new FolderBrowserDialog())
            {
                dlg.SelectedPath = _txtLogDir.Text;
                if (dlg.ShowDialog() == DialogResult.OK)
                {
                    _txtLogDir.Text = dlg.SelectedPath;
                }
            }
        }

        private void BtnToggle_Click(object sender, EventArgs e)
        {
            if (!_isRecording)
            {
                // 記録開始
                try
                {
                    if (!Directory.Exists(_txtLogDir.Text))
                    {
                        Directory.CreateDirectory(_txtLogDir.Text);
                    }

                    _manager = new TaskMinerManager(this, _txtLogDir.Text);
                    _manager.Start();

                    _isRecording = true;
                    _btnToggle.Text = "記録停止";
                    _btnToggle.ForeColor = Color.Blue;
                    _lblStatus.Text = "状態: 記録中...";
                    _txtLogDir.Enabled = false;
                }
                catch (Exception ex)
                {
                    MessageBox.Show("記録の開始に失敗しました。\n" + ex.Message, "エラー", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            }
            else
            {
                // 記録停止
                if (_manager != null)
                {
                    _manager.Stop();
                    _manager = null;
                }

                _isRecording = false;
                _btnToggle.Text = "記録開始";
                _btnToggle.ForeColor = Color.Red;
                _lblStatus.Text = "状態: 記録停止。出力可能です。";
                _txtLogDir.Enabled = true;
            }
        }

        private void MainForm_FormClosing(object sender, FormClosingEventArgs e)
        {
            if (_manager != null)
            {
                _manager.Stop();
            }
        }
    }
}
