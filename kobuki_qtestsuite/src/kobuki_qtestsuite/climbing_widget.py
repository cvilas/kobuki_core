import os
from QtCore import Signal, Slot
from QtGui import QWidget
import math

import roslib
roslib.load_manifest('kobuki_qtestsuite')
import rospy

from python_qt_binding import loadUi
#from python_qt_binding.QtGui import QWidget
from rqt_py_common.extended_combo_box import ExtendedComboBox
from qt_gui_py_common.worker_thread import WorkerThread

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

# Local resource imports
import resources.common
import resources.climbing

class ClimbingWidget(QWidget):

    def __init__(self, parent=None):
        super(ClimbingWidget, self).__init__(parent)
        
        # get path to UI file which is a sibling of this file
        # in this example the .ui file is in the same folder as this Python file
        ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ui', 'climbing.ui')
        # extend the widget with all attributes and children from UI file
        loadUi(ui_file, self, {'ExtendedComboBox': ExtendedComboBox})

        # give QObjects reasonable names
        self.setObjectName('ClimbingUi')
        
        _, _, topic_types = rospy.get_master().getTopicTypes()
        cmd_vel_topics = [ topic[0] for topic in topic_types if topic[1] == 'geometry_msgs/Twist' ]
        self.cmd_vel_topic_combo_box.setItems.emit(sorted(cmd_vel_topics))
        self.cmd_vel_publisher = rospy.Publisher(str(self.cmd_vel_topic_combo_box.currentText()), Twist)
        odom_topics = [ topic[0] for topic in topic_types if topic[1] == 'nav_msgs/Odometry' ]
        self.odom_topic_combo_box.setItems.emit(sorted(odom_topics))
        self.odom_subscriber = rospy.Subscriber(str(self.odom_topic_combo_box.currentText()), Odometry, self.odometry_callback)
        # UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        self._run_thread = None
        self._current_pose = None
        self._starting_pose = None
        self._current_speed = 0.0
        
    def shutdown(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        self.cmd_vel_publisher.publish(cmd)
        self.cmd_vel_publisher.unregister()
        if self._run_thread:
            self._run_thread.kill()
        
    def odometry_callback(self, data):
        self._current_pose = data.pose.pose
        
    ##########################################################################
    # Slot Callbacks
    ##########################################################################
    @Slot(str)
    def on_cmd_vel_topic_combo_box_currentIndexChanged(self, topic_name):
        # This is probably a bit broken, need to test with more than just /cmd_vel so
        # there is more than one option.
        self.cmd_vel_publisher = rospy.Publisher(str(self.cmd_vel_topic_combo_box.currentText()), Twist)

    @Slot(str)
    def on_odom_topic_combo_box_currentIndexChanged(self, topic_name):
        # Need to redo the subscriber here
        pass

    @Slot()
    def on_start_button_clicked(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._starting_pose = self._current_pose
        self._run_thread = WorkerThread(self._run, self._run_finished)
        self._run_thread.start()

    @Slot()
    def on_stop_button_clicked(self):
        '''
          Hardcore stoppage - straight to zero.
        '''
        self._run_thread.kill()
        cmd = Twist()
        cmd.linear.x = 0.0
        self.cmd_vel_publisher.publish(cmd)
        self._stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _soft_stop(self):
        rate = rospy.Rate(10)
        while self._current_speed > 0.0:
            self._current_speed -= 0.01
            cmd = Twist()
            cmd.linear.x = self._current_speed
            self.cmd_vel_publisher.publish(cmd)
            rate.sleep()
        self._current_speed = 0.00
        cmd = Twist()
        cmd.linear.x = 0.0
        self.cmd_vel_publisher.publish(cmd)
        
    ##########################################################################
    # Thread
    ##########################################################################

    def _run(self):
        print "thread started"
        speed = self.speed_spinbox.value()
        distance_sq = self.distance_spinbox.value()*self.distance_spinbox.value()
        rate = rospy.Rate(10)
        self._current_speed = 0.0
        current_distance_sq = 0.0
        while current_distance_sq < distance_sq:
            current_distance_sq = (self._current_pose.position.x - self._starting_pose.position.x)*(self._current_pose.position.x - self._starting_pose.position.x) + \
                               (self._current_pose.position.y - self._starting_pose.position.y)*(self._current_pose.position.y - self._starting_pose.position.y)
            #current_distance += 0.01
            print("Distance %s"%math.sqrt(current_distance_sq))
            if self._current_speed < speed:
                self._current_speed += 0.01
            cmd = Twist()
            cmd.linear.x = self._current_speed
            self.cmd_vel_publisher.publish(cmd)
            rate.sleep()
        self._soft_stop()
    
    def _run_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    