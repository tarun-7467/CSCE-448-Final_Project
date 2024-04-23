import cv2
import numpy as np


# Patch Extraction - this is done in GetMask.py I believe. 
def get_patches_around_boundary(image, mask, patch_size):
    # Patch size has to be odd
    if patch_size % 2 == 0:
        patch_size += 1

    half_patch = patch_size // 2

    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boundary_patches = []

    for contour in contours:
        for point in contour:
            x, y = point[0]
            
            # Check if the patch around this point is fully within the image bounds
            if y - half_patch >= 0 and y + half_patch < image.shape[0] and x - half_patch >= 0 and x + half_patch < image.shape[1]:
                patch = image[y - half_patch:y + half_patch + 1, x - half_patch:x + half_patch + 1]
                boundary_patches.append(((x, y), patch))

    return boundary_patches


def boundary(img, x, y, window):
    img_height, img_width = img.shape[0], img.shape[1]
    x_left = x - window[0]
    x_right = x + window[0]
    y_top = y - window[1]
    y_bottom = y + window[1]
    if x_left < 0:
        x_left = 0
    if x_right >= img_width:
        x_right = img_width - 1
    if y_top < 0:
        y_top = 0
    if y_bottom >= img_height:
        y_bottom = img_height - 1
    return x_left, x_right, y_top, y_bottom
        

def compute_priority(img, fill_front, mask, window, point, threshold=0.001):
    
    confidence = (1 - mask).astype(np.float64)

    compute_confidence(fill_front, window, mask, point, img, confidence)

    # 2.2. Run Sobel edge detector to find the normal along the x- and y-axis.
    data = cv2.Sobel(src=mask.astype(float), ddepth=cv2.CV_64F, dx=1, dy=1, ksize=1)
    # Normalize the vector.
    data /= np.linalg.norm(data)
    # This helps nudge the algorithm if it gets stuck.
    data +=  threshold

    # 2.3. Find the priority.
    priority = fill_front * confidence * data
    return priority, confidence


def compute_confidence(countours, windowSize, mask, point, sourceImage, confidence):
    radius = windowSize // 2
    inverseMask = 1-mask 
    inversedImage = inverseMask * sourceImage
    
    height, width = mask.shape #height is number rows, width is number of columns
    
    for front in np.argwhere(countours == 1): #along the fill front
        
        y_lower = max(0, point[0] - radius) #height lower bound is either 0 or point - radius
        y_upper = min(point[0] + radius, height - 1) #height upper bound is either the point + radius, or the height of the pic
        x_lower = max(0, point[1] - radius)
        x_upper = min(point[1], width - 1)
        
        psi = confidence[y_lower:y_upper , x_lower:x_upper]
        sumPsi = np.sum(psi)
        magPsi = (x_upper - x_lower) * (y_upper - y_lower)
        confidence[point[1], point[0]] = sumPsi / magPsi

    return confidence
        
#function should be good and done - allen
def find_best_match(image, target_patch, mask, patch_size):
    best_ssd = float('inf')
    best_match = []
    half_patch_size = patch_size // 2
    inverted_mask = 1 - mask

    for y in range(half_patch_size, image.shape[0] - half_patch_size): 
        #making sure it doesn't start or end too close to the edge of the image
        for x in range(half_patch_size, image.shape[1] - half_patch_size):
            # Skip patches that overlap with the mask
            bottomY = y - half_patch_size
            upperY = y + half_patch_size + 1
            bottomX = x - half_patch_size
            upperX = x + half_patch_size + 1
            maskPatch = inverted_mask[bottomY:upperY, bottomX:upperX]
            # if any of the points within the mask patch are equal to 1, skip to the next spot
            if np.any(maskPatch == 0):
                continue
            
            candidatePatch = image[bottomY:upperY, bottomX:upperX] * inverted_mask
            # multiplying by inverted mask ^^^ should not matter since any patches within the mask are skipped
            targetImage = target_patch * inverted_mask #all points within the mask will be 0 and points outside will be the same
            #only comparing points outside of the mask here
            
            difference = np.linalg.norm(targetImage - candidatePatch)
            
            if difference < best_ssd:
                best_ssd = difference
                best_match = [bottomX, upperX, bottomY,upperY]
                # returns an array which which has the bottom and top x and y values of the box we should use to fill the 
                #patch that we need
                
    return best_match
                
        

def inpaint(image, mask, patch_size):
    # Convert the mask to a binary format if it isn't already
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    while np.any(mask):
        boundary_patches = get_patches_around_boundary(image, mask, patch_size)

        highest_priority = -1
        best_patch = None
        best_patch_pos = None

        for pos, patch in boundary_patches:
            grad_patch = grad_mag[pos[1] - patch_size // 2:pos[1] + patch_size // 2 + 1,
                                  pos[0] - patch_size // 2:pos[0] + patch_size // 2 + 1]
            priority = compute_priority(patch, grad_patch)

            if priority > highest_priority:
                highest_priority = priority
                best_patch = patch
                best_patch_pos = pos

        best_match_pos = find_best_match(image, best_patch, mask)
        x, y = best_patch_pos
        match_x, match_y = best_match_pos

        # Copy the best matching patch into the target position
        image[y - patch_size // 2:y + patch_size // 2 + 1, x - patch_size // 2:x + patch_size // 2 + 1] = \
            image[match_y - patch_size // 2:match_y + patch_size // 2 + 1, match_x - patch_size // 2:match_x + patch_size // 2 + 1]

        # Update the mask
        mask[y - patch_size // 2:y + patch_size // 2 + 1, x - patch_size // 2:x + patch_size // 2 + 1] = 0

    return image

def update_Mask_Image(): 
    return 0


if __name__ == '__main__':
    # # Parameters
    # patch_size = 9  # Example patch size

    # # Compute the gradient magnitude of the image (for the data term)
    # grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
    # grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
    # grad_mag = cv2.magnitude(grad_x, grad_y)

    # # Get patches around the boundary
    # boundary_patches = get_patches_around_boundary(image, mask, patch_size)

    # # Compute priority for each patch (for illustration; in practice, this ties into the inpainting loop)
    # for pos, patch in boundary_patches:
    #     # Extract the corresponding gradient magnitude patch
    #     grad_patch = grad_mag[pos[1] - patch_size // 2:pos[1] + patch_size // 2 + 1,
    #                         pos[0] - patch_size // 2:pos[0] + patch_size // 2 + 1]
        
    #     priority = compute_priority(patch, grad_patch)
    #     print(f"Patch at {pos} has priority {priority}")

    # Load the image and mask
    image = cv2.imread('path_to_your_image.jpg', 0)  # Load as grayscale for simplicity
    mask = cv2.imread('path_to_your_mask.jpg', 0)  # Assume mask is also grayscale

    # Ensure the mask is a binary image
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # Define patch size
    patch_size = 9

    # Perform inpainting
    inpainted_image = inpaint(image, mask, patch_size)

    # Display the results
    cv2.imshow("Original Image", image)
    cv2.imshow("Mask", mask)
    cv2.imshow("Inpainted Image", inpainted_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()




