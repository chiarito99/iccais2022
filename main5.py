from cmath import nan
from operator import length_hint
from tkinter import W
import numpy as np
import math
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d
from Plotting5 import Plotting
from env import Env
from sklearn.metrics import jaccard_score
from sweep_line_has_bad import getConvexPolygon,computeWLofCamera
global flag,err1,err2,cons,a,f1,f2,vleader
class LeaderUAV:
    def __init__(self, pos=[0,0,0]):
        # Configuration
        self.pos = np.array(pos)
        self.heading = 0
        self.path = [self.pos]

        # Control parameters
        self.am = 3.8
        self.bm = 1.0
        self.ao = 3.0
        self.bo = 4.0
        self.do = 1.5


    def move_to_goal(self, goal):
        dm = math.sqrt((goal[0]-self.pos[0])**2 + (goal[1]-self.pos[1])**2 + (goal[2]-self.pos[2])**2)
        vm2g = (goal-self.pos)/dm    # Velocity move to goal
        fm2g = self.am               # Control parameter of vm2g
        if dm <= self.bm:
            fm2g = self.am*dm/self.bm
        return 2.3*fm2g*vm2g

    def avoid_obstacle(self, obs):
        v = np.zeros(np.size(self.pos))
        for i in range(len(obs)):
            do = math.sqrt((obs[i,0]-self.pos[0])**2 + (obs[i,1]-self.pos[1])**2) - obs[i,2] - 0.5
            vao = (obs[i,:2]-self.pos[:2])/do          # Velocity avoiding obstacle
            sig = -np.sign(vao[0]*math.sin(self.heading)-vao[1]*math.cos(self.heading))
            rot = np.array([[0,-sig,0],[sig,0,0],[0,0,1]])
            fao = 0
            vao = np.array([vao[0],vao[1],0])
            if do <= self.bo :
                fao = self.ao*(1-do/self.bo)
            v = v + (fao*rot)@vao
        return v



    def control_signal(self, ref, obs,flag,err1,err2,err3,err4):
        v1 = self.move_to_goal(ref)
        if flag == 1:
            v1= 1/(self.do*max(err1-cons,err2-cons,err3-cons,err4-cons)) * v1
            if max(err1-cons,err2-cons,err3-cons,err4-cons) < self.do:
                v1 =  self.bm*max(err1-cons,err2-cons,err3-cons,err4-cons)/self.am * v1
        v2 = self.avoid_obstacle(obs)
        return v1 + v2
    
    def update_position(self, vel, dt=0.1):
        self.pos = self.pos + vel*dt
        self.heading = (np.arctan2(vel[1], vel[0]) + np.pi) %(2*np.pi)-np.pi
        self.path.append(self.pos)

class FollowerUAV:
    def __init__(self, pos=[0,0,0], leader=None, delta=[0,0],wp= None):
        # Configuration
        self.pos = np.array(pos)
        self.heading = 0
        self.wp = wp
        if leader == None:
            self.leader = LeaderUAV()
        else:
            self.leader = leader
        self.delta = delta
        self.path = [self.pos]

        # Control parameters
        self.am = 3.3
        self.bm = 1.0
        self.ao = 3.0
        self.bo = 4.0


    def avoid_Robot(self,rbt_pos):
        v = np.zeros(np.size(self.pos))
        for i in range(len(rbt_pos)):
            do = math.sqrt((rbt_pos[i,0]-self.pos[0])**2 + (rbt_pos[i,1]-self.pos[1])**2)
            e=0
            if do !=0 and do<0.1:
                e = -(rbt_pos[i,:2]-self.pos[:2])/do
                vao = np.array([e[0],e[1],0])
                v=v+vao
            else:
                v=v
        return v



    def keep_formation(self, ref,flag,a,f1):
        print(a)
        xr = np.cos(self.leader.heading)*self.delta[0] - np.sin(self.leader.heading)*self.delta[1] + ref[0]
        yr = np.sin(self.leader.heading)*self.delta[0] + np.cos(self.leader.heading)*self.delta[1] + ref[1]
        zr = ref[2]
        pr = np.array([xr, yr, zr])
        phi1 = 0
        f1 = pr - self.pos
        # print(f1)
        phi1 = np.arccos((f1[0]*a[0]+f1[1]*a[1])/((np.hypot(f1[0],f1[1]))*(np.hypot(a[0],a[1]))))
        if phi1 == nan:
            phi1=0
        dk = math.sqrt((xr-self.pos[0])**2 + (yr-self.pos[1])**2 + (zr-self.pos[2])**2)
        vkf = (pr-self.pos)/dk# Velocity move to goal
        for i in range(1,len(self.wp)-1):
            # wk =math.sqrt((xr-waypoint[0])**2 + (yr-waypoint[1])**2)
            wk = math.sqrt((xr-self.wp[i][0])**2 + (yr-self.wp[i][1])**2)     
            if (3 <wk < 9.5 or 11< wk<18 ) and  (phi1 > np.pi/2 or flag ==2):
                vkf = vleader/100
            else:
                vkf= vkf

        fkf = self.am              # Control parameter of vm2g
        if dk <= self.bm:
            fkf = self.am*dk/self.bm
        return 2.2*fkf*vkf

    def avoid_obstacle(self, obs):
        v = np.zeros(np.size(self.pos))
        for i in range(len(obs)):
            do = math.sqrt((obs[i,0]-self.pos[0])**2 + (obs[i,1]-self.pos[1])**2) - obs[i,2]-0.5
            vao = (obs[i,:2]-self.pos[:2])/do          # Velocity avoiding obstacle
            sig = -np.sign(vao[0]*math.sin(self.heading)-vao[1]*math.cos(self.heading))
            rot = np.array([[0,-sig,0],[sig,0,0],[0,0,1]])
            fao = 0
            vao = np.array([vao[0],vao[1],0])
            if do <= self.bo :
                fao = self.ao*(1-do/self.bo)
            v = v + (fao*rot)@vao
        return v

    

    def control_signal(self, ref, obs,rbt_pos):
        v1 = self.keep_formation(ref,flag,a,f1)
        v2 = 1.3*self.avoid_obstacle(obs)
        v3 = self.avoid_Robot(rbt_pos)
        if v2[1] == 0 and flag == 0 :
            v1 = 1.3*v1
        else:
            v1= v1
        return v1 +v2+v3
    
    def update_position(self, vel, dt=0.1):
        self.pos = self.pos + vel*dt
        self.heading = (np.arctan2(vel[1], vel[0]) + np.pi) %(2*np.pi)-np.pi
        self.path.append(self.pos)



def plot_obstacles(ox, oy, oz, r):
    z = np.linspace(0, oz, 50)
    theta = np.linspace(0, 2*np.pi, 50)
    theta_grid, z_grid=np.meshgrid(theta, z)
    x_grid = r*np.cos(theta_grid) + ox
    y_grid = r*np.sin(theta_grid) + oy
    return x_grid,y_grid,z_grid

def giaiPTBac2(a, b, c):
    delta = b * b - 4 * a * c
    if (delta > 0):
        x1 = (float)((-b + math.sqrt(delta)) / (2 * a));
        x2 = (float)((-b - math.sqrt(delta)) / (2 * a));
    elif (delta == 0):
        x1 = (-b / (2 * a))
    else:
        print("Phương trình vô nghiệm!")
    return x1,x2

def overlap(width,length,percenoverlap):
    indicator = (percenoverlap *width *length)/(2*width *length*2)
    x1,x2 = giaiPTBac2(-1,1,-indicator)
    if x1<x2:
        return x1
    else:
        return x2

def calculateover(width,length,percen):
    width_s = width * percen
    length_s = length * percen
    offset_x = width - width_s
    offset_y = length - length_s
    resolution = 3*(offset_y + length/2)- 2*length_s
    return offset_x,offset_y,resolution


if __name__ == "__main__":
    dt = 0.1  # time step
    
    x_start = -80
    y_start = -80
    x_end = 80
    y_end = 80
    K = [[58.98295314305732, -40.46389776524755], [-19.5748849118947, -78.531936254165], [-62.674712335622026, 24.06481669719506], [-31.09947113556031, 61.08658069805723], [52.20911077098446, 26.412130624396212]]

    # Calculate L&W of one Camera
    alpha = 0.15 # Góc máy  chiều rộng
    beta = 0.22 # GÓc máy chiều 
    altitude = 20
    percenoverlap = 0.3
    width , length = computeWLofCamera(altitude,alpha,beta)
    xxx = overlap(width,length,percenoverlap)
    offsetx,offsety,resolution = calculateover(width,length,xxx)
    disLF = np.hypot(offsetx,offsety)
    cons = disLF
    map = Env(K,x_start,y_start,x_end,y_end,altitude,resolution)
    K.append(K[0])
    ox, oy = zip(*K)
    pt = map.point
    flag = 0
    err1 = 0
    err2 = 0
    err3 = 0
    err4 = 0
    a = [0]
    f1 = [0]
    f2 = [0]
    # Formation processing
    leader = LeaderUAV(pos=[x_start,y_start,0])
    follower1 = FollowerUAV(pos=[x_start,y_start,0],leader=leader, delta=[-offsetx,-offsety],wp = pt)
    follower2 = FollowerUAV(pos=[x_start,y_start,0],leader=leader, delta=[-offsetx, offsety],wp = pt)
    follower3 = FollowerUAV(pos=[x_start,y_start,0],leader=leader, delta=[-2*offsetx, -2*offsety],wp = pt)
    follower4 = FollowerUAV(pos=[x_start,y_start,0],leader=leader, delta=[-2*offsetx, 2*offsety],wp = pt)
    x_traj, y_traj = [], []
    for i in range(len(map.traj[0])):
        ref = map.traj[:,i]
        a = ref-a
        x_traj.append(ref[0])
        # print(x_traj)
        y_traj.append(ref[1])
        # print()
        # Check if the traj is colision
        is_colision = False
        for i in range(len(map.obs)):
            do = math.sqrt((ref[0]-map.obs[i,0])**2 + (ref[1]-map.obs[i,1])**2)
            bias = 2.0
            if do <= map.obs[i,2] + bias:
                is_colision = True
                break
        if is_colision:
            continue
        rbt_pos = np.array([follower1.pos,follower2.pos])
        # UAV processing
        lvel = leader.control_signal(ref, map.obs,flag,err1,err2,err3,err4)
        f1vel = follower1.control_signal(ref, map.obs,rbt_pos)
        f2vel = follower2.control_signal(ref, map.obs,rbt_pos)
        f3vel = follower3.control_signal(ref, map.obs,rbt_pos)
        f4vel = follower4.control_signal(ref, map.obs,rbt_pos)
        # UAV update
        leader.update_position(lvel)
        a=leader.pos
        vleader = lvel
        follower1.update_position(f1vel)
        follower2.update_position(f2vel)
        follower3.update_position(f3vel)
        follower4.update_position(f4vel)

        err1 = np.hypot((leader.pos[0]-follower1.pos[0]),(leader.pos[1]-follower1.pos[1]))
        err2 = np.hypot((leader.pos[0]-follower2.pos[0]),(leader.pos[1]-follower2.pos[1]))
        err3 = np.hypot((leader.pos[0]-follower3.pos[0]),(leader.pos[1]-follower3.pos[1]))
        err4 = np.hypot((leader.pos[0]-follower4.pos[0]),(leader.pos[1]-follower4.pos[1]))
        if 3 < err1+err2+err3+err4- 6*disLF < 5:
            flag = 1
        elif abs(leader.heading - follower1.heading) >np.pi/2 or abs(leader.heading - follower2.heading) >np.pi/2 :
            flag =2
        else:
            flag = 0
    # # print(leader.path)
    plot= Plotting("formation")
    plot.plot_animation(leader.path,follower1.path,follower2.path,follower3.path,follower4.path,ox, oy,x_start,y_start,x_end,y_end,length,width,map.obs)
    plt.show()
    
    # Plotting
    plt.figure()
    ax = plt.axes(projection ='3d')
    ax.plot(map.ox, map.oy, np.ones(len(map.ox))*map.altitude, '-xk', label='range')
    ax.plot(map.traj[0,:], map.traj[1,:], map.traj[2,:], '-b', label='reference')

    # plot obstacle
    for i in range(len(map.obs)):
        Xc, Yc, Zc = plot_obstacles(map.obs[i,0], map.obs[i,1], 1.2*map.altitude, map.obs[i,2])
        ax.plot_surface(Xc, Yc, Zc, alpha=0.5)

    leader.path = np.array(leader.path)
    follower1.path = np.array(follower1.path)
    follower2.path = np.array(follower2.path)
    follower3.path = np.array(follower3.path)
    follower4.path = np.array(follower4.path)
    # follower2.path = np.array(follower2.path)
    ax.plot(leader.path[:,0], leader.path[:,1], leader.path[:,2], '--r', label='leader UAV')
    ax.plot(follower1.path[:,0], follower1.path[:,1], follower1.path[:,2], '--g', label='follower 1 UAV')
    ax.plot(follower2.path[:,0], follower2.path[:,1], follower2.path[:,2], '--g', label='follower 2 UAV')
    ax.plot(follower3.path[:,0], follower3.path[:,1], follower3.path[:,2], '--g', label='follower 2 UAV')
    ax.plot(follower4.path[:,0], follower4.path[:,1], follower4.path[:,2], '--g', label='follower 2 UAV')
    ax.plot(map.traj[0,0], map.traj[1,0], map.traj[2,0], 'ks', label='start')    # start
    ax.plot(map.traj[0,-1], map.traj[1,-1], map.traj[2,-1], 'ko', label='end')    # end
    

    ax.set_title("Forest rangers")
    ax.grid(True)
    ax.set_xlabel('x [m]')
    ax.set_ylabel('y [m]')
    ax.set_zlabel('z [m]')
    ax.legend()
    plt.show()