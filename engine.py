from config import *
import megatexture

class Engine:
    """
        Responsible for drawing scenes
    """

    def __init__(self, width, height):
        """
            Initialize a flat raytracing context
            
                Parameters:
                    width (int): width of screen
                    height (int): height of screen
        """
        self.screenWidth = width
        self.screenHeight = height

        self.targetFrameRate = 60
        self.frameRateMargin = 10

        #general OpenGL configuration
        self.shader = self.createShader("shaders/frameBufferVertex.txt",
                                        "shaders/frameBufferFragment.txt")
        
        self.rayTracerShader = self.createComputeShader("shaders/rayTracer.txt")
        
        glUseProgram(self.shader)
        
        self.createQuad()
        self.createLODChain()
        self.createColorBuffers()
        self.createResourceMemory()
        self.createNoiseTexture()
        self.createMegaTexture()
    
    def createLODChain(self):

        self.resolutions = [(self.screenWidth, self.screenHeight)]

        width,height = (self.screenWidth,self.screenHeight)
        while width > 2 and height > 2:
            width = int(width / 1.25)
            height = int(height / 1.25)
            self.resolutions.append((width, height))
        
        self.resolutionLevel = len(self.resolutions) - 1
        
        self.screenWidth,self.screenHeight = self.resolutions[self.resolutionLevel]
    
    def createQuad(self):
        # x, y, z, s, t
        self.vertices = np.array(
            ( 1.0,  1.0, 0.0, 1.0, 1.0, #top-right
             -1.0,  1.0, 0.0, 0.0, 1.0, #top-left
             -1.0, -1.0, 0.0, 0.0, 0.0, #bottom-left
             -1.0, -1.0, 0.0, 0.0, 0.0, #bottom-left
              1.0, -1.0, 0.0, 1.0, 0.0, #bottom-right
              1.0,  1.0, 0.0, 1.0, 1.0), #top-right
             dtype=np.float32
        )

        self.vertex_count = 6

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(12))
    
    def createColorBuffers(self):

        self.colorBuffers = []

        for resolution in self.resolutions:

            width,height = resolution

            newColorBuffer = glGenTextures(1)
            self.colorBuffers.append(newColorBuffer)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, newColorBuffer)

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)

        
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, width, height, 0, GL_RGBA, GL_FLOAT, None)
        
        self.colorBuffer = self.colorBuffers[self.resolutionLevel]
    
    def createResourceMemory(self):

        """
            allocate storage for up to 1024 objects (why not?)
        """

        objectData = []

        # sphere: (cx cy cz r)  (r g b roughness) (- - - -)     (- - - -)             (- - - -)
        # plane:  (cx cy cz tx) (ty tz bx by)     (bz nx ny nz) (umin umax vmin vmax) (material_index - - -)
        # light:  (x y z s)     (r g b -)         (bz nx ny nz) (umin umax vmin vmax) (material_index - - -)
        for object in range(1024):
            for attribute in range(20):
                objectData.append(0.0)
        self.objectData = np.array(objectData, dtype=np.float32)

        self.objectDataTexture = glGenTextures(1)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.objectDataTexture)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,5,1024,0,GL_RGBA,GL_FLOAT,bytes(self.objectData))

    def createNoiseTexture(self):

        """
            generate four screens' worth of noise
        """

        noise = []

        # random noise: (x y z -)
        for y in range(600):
            for x in range(800 * 4):
                radius = np.random.uniform(low = 0.0, high = 0.99)
                theta = np.random.uniform(low = 0.0, high = 2 * np.pi)
                phi = np.random.uniform(low = 0.0, high = np.pi)
                noise.append(radius * np.cos(theta) * np.cos(phi))
                noise.append(radius * np.sin(theta) * np.cos(phi))
                noise.append(radius * np.sin(phi))
                noise.append(0.0)
        self.noiseData = np.array(noise, dtype=np.float32)

        self.noiseTexture = glGenTextures(1)
        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.noiseTexture)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    
        glTexImage2D(
            GL_TEXTURE_2D,0,GL_RGBA32F, 
            4 * 800,600,
            0,GL_RGBA,GL_FLOAT,bytes(self.noiseData)
        )
    
    def createMegaTexture(self):

        filenames = [
            "AlienArchitecture", "AlternatingColumnsConcreteTile", "BiomechanicalPlumbing", 
            "CarvedStoneFloorCheckered", "ChemicalStrippedConcrete", "ClayBrick",
            "CrumblingBrickWall", "DiamondSquareFlourishTiles", "EgyptianHieroglyphMetal"
        ]

        self.megaTexture = megatexture.MegaTexture(filenames)
    
    def createShader(self, vertexFilepath, fragmentFilepath):
        """
            Read source code, compile and link shaders.
            Returns the compiled and linked program.
        """

        with open(vertexFilepath,'r') as f:
            vertex_src = f.readlines()

        with open(fragmentFilepath,'r') as f:
            fragment_src = f.readlines()
        
        shader = compileProgram(compileShader(vertex_src, GL_VERTEX_SHADER),
                                compileShader(fragment_src, GL_FRAGMENT_SHADER))
        
        return shader
    
    def createComputeShader(self, filepath):
        """
            Read source code, compile and link shaders.
            Returns the compiled and linked program.
        """

        with open(filepath,'r') as f:
            compute_src = f.readlines()
        
        shader = compileProgram(compileShader(compute_src, GL_COMPUTE_SHADER))
        
        return shader

    def recordSphere(self, i, _sphere):

        # sphere: (cx cy cz r) (r g b -) (- - - -) (- - - -) (- - - -)

        self.objectData[20*i]     = _sphere.center[0]
        self.objectData[20*i + 1] = _sphere.center[1]
        self.objectData[20*i + 2] = _sphere.center[2]

        self.objectData[20*i + 3] = _sphere.radius

        self.objectData[20*i + 4] = _sphere.color[0]
        self.objectData[20*i + 5] = _sphere.color[1]
        self.objectData[20*i + 6] = _sphere.color[2]

        self.objectData[20*i + 7] = _sphere.roughness
    
    def recordPlane(self, i, _plane):

        # plane: (cx cy cz tx) (ty tz bx by) (bz nx ny nz) (umin umax vmin vmax) (r g b -)

        self.objectData[20*i]     = _plane.center[0]
        self.objectData[20*i + 1] = _plane.center[1]
        self.objectData[20*i + 2] = _plane.center[2]

        self.objectData[20*i + 3] = _plane.tangent[0]
        self.objectData[20*i + 4] = _plane.tangent[1]
        self.objectData[20*i + 5] = _plane.tangent[2]

        self.objectData[20*i + 6] = _plane.bitangent[0]
        self.objectData[20*i + 7] = _plane.bitangent[1]
        self.objectData[20*i + 8] = _plane.bitangent[2]

        self.objectData[20*i + 9]  = _plane.normal[0]
        self.objectData[20*i + 10] = _plane.normal[1]
        self.objectData[20*i + 11] = _plane.normal[2]

        self.objectData[20*i + 12] = _plane.uMin
        self.objectData[20*i + 13] = _plane.uMax
        self.objectData[20*i + 14] = _plane.vMin
        self.objectData[20*i + 15] = _plane.vMax

        self.objectData[20*i + 16] = _plane.material_index
    
    def recordLight(self, i, _light):

        # light: (x y z s) (r g b -) (- - - -) (- - - -) (- - - -)

        self.objectData[20*i]     = _light.position[0]
        self.objectData[20*i + 1] = _light.position[1]
        self.objectData[20*i + 2] = _light.position[2]
        self.objectData[20*i + 3] = _light.strength

        self.objectData[20*i + 4] = _light.color[0]
        self.objectData[20*i + 5] = _light.color[1]
        self.objectData[20*i + 6] = _light.color[2]
    
    def updateScene(self, scene):

        scene.outDated = False

        glUseProgram(self.rayTracerShader)

        #spheres
        sphereCount = 0
        objectCount = 0
        for i,_sphere in enumerate(scene.spheres):
            self.recordSphere(i + sphereCount + objectCount, _sphere)
        sphereCount += len(scene.spheres)
        for room in scene.active_rooms:
            for i, _sphere in enumerate(room.spheres):
                self.recordSphere(i + sphereCount + objectCount, _sphere)
            sphereCount += len(room.spheres)
        glUniform1f(glGetUniformLocation(self.rayTracerShader, "sphereCount"), sphereCount)
        objectCount += sphereCount

        #planes
        planeCount = 0
        for i,_plane in enumerate(scene.planes):
            self.recordPlane(i + planeCount + objectCount, _plane)
        planeCount += len(scene.planes)
        for room in scene.active_rooms:
            for i, _plane in enumerate(room.planes):
                self.recordPlane(i + planeCount + objectCount, _plane)
            planeCount += len(room.planes)
            for door in room.doors:
                for i,_plane in enumerate(door.planes):
                    self.recordPlane(i + planeCount + objectCount, _plane)
                planeCount += len(door.planes)
        glUniform1f(glGetUniformLocation(self.rayTracerShader, "planeCount"), planeCount)
        objectCount += planeCount

        #lights
        lightCount = 0
        for i,_light in enumerate(scene.lights):
            self.recordLight(i + lightCount + objectCount, _light)
        lightCount += len(scene.lights)
        for room in scene.active_rooms:
            for i, _light in enumerate(room.lights):
                self.recordLight(i + lightCount + objectCount, _light)
            lightCount += len(room.lights)
        glUniform1f(glGetUniformLocation(self.rayTracerShader, "lightCount"), lightCount)
        objectCount += lightCount

        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.objectDataTexture)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,5,1024,0,GL_RGBA,GL_FLOAT,bytes(self.objectData))

    def prepareScene(self, scene):
        """
            Send scene data to the shader.
        """

        glUseProgram(self.rayTracerShader)

        glUniform3fv(glGetUniformLocation(self.rayTracerShader, "viewer.position"), 1, scene.camera.position)
        glUniform3fv(glGetUniformLocation(self.rayTracerShader, "viewer.forwards"), 1, scene.camera.forwards)
        glUniform3fv(glGetUniformLocation(self.rayTracerShader, "viewer.right"), 1, scene.camera.right)
        glUniform3fv(glGetUniformLocation(self.rayTracerShader, "viewer.up"), 1, scene.camera.up)

        if scene.outDated:
            self.updateScene(scene)
        
        glActiveTexture(GL_TEXTURE1)
        glBindImageTexture(1, self.objectDataTexture, 0, GL_FALSE, 0, GL_READ_ONLY, GL_RGBA32F)

        glActiveTexture(GL_TEXTURE2)
        glBindImageTexture(2, self.noiseTexture, 0, GL_FALSE, 0, GL_READ_ONLY, GL_RGBA32F)

        glActiveTexture(GL_TEXTURE3)
        glBindImageTexture(3, self.megaTexture.texture, 0, GL_FALSE, 0, GL_READ_ONLY, GL_RGBA32F)
        
    def renderScene(self, scene):
        """
            Draw all objects in the scene
        """
        
        glUseProgram(self.rayTracerShader)

        self.prepareScene(scene)

        glActiveTexture(GL_TEXTURE0)
        glBindImageTexture(0, self.colorBuffer, 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_RGBA32F)
        
        glDispatchCompute(self.screenWidth, self.screenHeight, 1)
  
        # make sure writing to image has finished before read
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)
        glBindImageTexture(0, 0, 0, GL_FALSE, 0, GL_WRITE_ONLY, GL_RGBA32F)
        self.drawScreen()

    def drawScreen(self):
        glUseProgram(self.shader)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.colorBuffer)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)
        pg.display.flip()
    
    def adaptResolution(self, frameRate):

        if frameRate > self.targetFrameRate + self.frameRateMargin and self.resolutionLevel > 0:
            #increase resolution
            self.resolutionLevel -= 1
        elif frameRate < self.targetFrameRate - self.frameRateMargin and self.resolutionLevel < len(self.resolutions) - 1:
            #reduce resolution
            self.resolutionLevel += 1
        
        self.screenWidth,self.screenHeight = self.resolutions[self.resolutionLevel]
        self.colorBuffer = self.colorBuffers[self.resolutionLevel]
    
    def destroy(self):
        """
            Free any allocated memory
        """
        glUseProgram(self.rayTracerShader)
        glMemoryBarrier(GL_ALL_BARRIER_BITS)
        glDeleteProgram(self.rayTracerShader)
        glDeleteVertexArrays(1, (self.vao,))
        glDeleteBuffers(1, (self.vbo,))
        glDeleteTextures(1, (self.colorBuffer,))
        glDeleteProgram(self.shader)